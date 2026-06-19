# -*- coding: utf-8 -*-
"""Vendor product file imports.

A vendor uploads a CSV or Excel file; it is parsed into editable staged lines
the vendor can fix, then submitted for Uellow review. On approval each line
becomes a product (pending product approval), scoped to the vendor's markets.
"""
import base64
import csv
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Accepted header aliases → canonical field.
_COLMAP = {
    'name_en': 'name_en', 'name': 'name_en', 'title': 'name_en', 'english name': 'name_en',
    'name_ar': 'name_ar', 'arabic name': 'name_ar', 'الاسم': 'name_ar',
    'sku': 'sku', 'default_code': 'sku', 'code': 'sku',
    'barcode': 'barcode', 'ean': 'barcode',
    'cost': 'cost', 'standard_price': 'cost',
    'price': 'price', 'list_price': 'price', 'sale price': 'price',
    'category': 'category', 'categ': 'category',
    'description': 'description', 'desc': 'description',
}


class UellowProductImport(models.Model):
    _name = 'uellow.product.import'
    _description = 'Vendor Product Import File'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    vendor_id = fields.Many2one('uellow.vendor', string='Vendor',
                                required=True, index=True, ondelete='cascade')
    file_name = fields.Char('File Name')
    file_data = fields.Binary('File', attachment=True)
    line_ids = fields.One2many('uellow.product.import.line', 'import_id', string='Rows')
    state = fields.Selection([
        ('draft',    'Draft (editing)'),
        ('review',   'Pending Review'),
        ('done',     'Imported'),
        ('rejected', 'Rejected'),
    ], default='draft', required=True, index=True, tracking=True)
    note = fields.Char('Admin Note')
    row_count = fields.Integer('Rows', compute='_compute_counts', store=True)
    error_count = fields.Integer('Errors', compute='_compute_counts', store=True)
    created_count = fields.Integer('Created', readonly=True, copy=False)

    @api.depends('line_ids', 'line_ids.error')
    def _compute_counts(self):
        for r in self:
            r.row_count = len(r.line_ids)
            r.error_count = len(r.line_ids.filtered(lambda l: l.error))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uellow.product.import') or _('IMP/%s') % fields.Datetime.now().strftime('%y%m%d%H%M%S')
        return super().create(vals_list)

    # ── Parsing ─────────────────────────────────────────────────────
    def _parse_file(self):
        """Populate line_ids from the uploaded CSV/Excel file."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('No file uploaded.'))
        raw = base64.b64decode(self.file_data)
        fname = (self.file_name or '').lower()
        rows = []
        if fname.endswith('.xlsx') or raw[:2] == b'PK':
            rows = self._parse_xlsx(raw)
        else:
            rows = self._parse_csv(raw)
        self.line_ids.unlink()
        Line = self.env['uellow.product.import.line']
        seq = 0
        for row in rows:
            seq += 1
            vals = {'import_id': self.id, 'sequence': seq}
            for k, v in row.items():
                canon = _COLMAP.get((k or '').strip().lower())
                if canon:
                    vals[canon] = (str(v).strip() if v is not None else '')
            ln = Line.create(vals)
            ln._validate()
        return True

    def _parse_csv(self, raw):
        text = raw.decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    def _parse_xlsx(self, raw):
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('Excel support is unavailable; please upload a CSV.'))
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() if h is not None else '' for h in rows[0]]
        out = []
        for r in rows[1:]:
            if not any(c is not None and str(c).strip() for c in r):
                continue
            out.append({headers[i]: r[i] for i in range(len(headers)) if i < len(r)})
        return out

    # ── Workflow ────────────────────────────────────────────────────
    def action_submit(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('Parse a file with at least one row first.'))
            r.state = 'review'
            r.message_post(body=_('Submitted for review (%d rows).') % len(r.line_ids))
            try:
                CN = self.env['mobile.customer.notification'].sudo()
                admins = CN._admin_partners()
                if admins:
                    CN.push_role('notify_product_import', admins,
                        title_en='Vendor bulk import to review',
                        title_ar='استيراد جماعي بانتظار المراجعة',
                        body_en='%s submitted %d products.' % (r.vendor_id.display_name, len(r.line_ids)),
                        body_ar='%s قدّم %d منتجاً.' % (r.vendor_id.display_name, len(r.line_ids)),
                        data={'type': 'product_import', 'id': r.id})
            except Exception:
                pass

    def action_mark_done(self):
        """Approve: create a product per valid line (pending product approval)."""
        from odoo import SUPERUSER_ID
        for r in self:
            senv = self.env(user=SUPERUSER_ID)
            Tmpl = senv['product.template']
            Cat = senv['product.public.category']
            created = 0
            for ln in r.line_ids:
                if ln.error or ln.created_product_id:
                    continue
                name = ln.name_en or ln.name_ar
                vals = {
                    'name': name,
                    'list_price': ln._num(ln.price),
                    'standard_price': ln._num(ln.cost),
                    'default_code': ln.sku or '',
                    'barcode': ln.barcode or False,
                    'description_sale': ln.description or '',
                    'vendor_id': r.vendor_id.id,
                    'vendor_approval_state': 'pending',
                    'vendor_submitted_by': r.vendor_id.user_id.id,
                    'is_published': False, 'sale_ok': True, 'purchase_ok': False,
                }
                if ln.category:
                    cat = Cat.search([('name', 'ilike', ln.category)], limit=1)
                    if cat:
                        vals['public_categ_ids'] = [(6, 0, cat.ids)]
                try:
                    t = Tmpl.create(vals)
                    if ln.name_ar:
                        t.with_context(lang='ar_001').write({'name': ln.name_ar})
                        if ln.name_en:
                            t.with_context(lang='en_US').write({'name': ln.name_en})
                    try:
                        r.vendor_id._apply_market_to_product(t)
                    except Exception:
                        pass
                    ln.created_product_id = t.id
                    created += 1
                except Exception as e:
                    ln.error = str(e)[:200]
            r.created_count = created
            r.state = 'done'
            r.message_post(body=_('Imported %d products.') % created)

    def action_reject(self):
        self.write({'state': 'rejected'})


class UellowProductImportLine(models.Model):
    _name = 'uellow.product.import.line'
    _description = 'Vendor Product Import Row'
    _order = 'sequence, id'

    import_id = fields.Many2one('uellow.product.import', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name_en = fields.Char('Name (EN)')
    name_ar = fields.Char('Name (AR)')
    sku = fields.Char('SKU')
    barcode = fields.Char('Barcode')
    cost = fields.Char('Cost')
    price = fields.Char('Price')
    category = fields.Char('Category')
    description = fields.Text('Description')
    error = fields.Char('Issue', readonly=True)
    created_product_id = fields.Many2one('product.template', readonly=True, copy=False)

    @staticmethod
    def _num(x):
        try:
            return float(str(x).strip())
        except (TypeError, ValueError):
            return 0.0

    def _validate(self):
        for ln in self:
            problems = []
            if not (ln.name_en or ln.name_ar):
                problems.append('missing name')
            if ln.price and ln._num(ln.price) <= 0:
                problems.append('bad price')
            ln.error = '; '.join(problems) or False

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('name_en', 'name_ar', 'price', 'cost')):
            self._validate()
        return res
