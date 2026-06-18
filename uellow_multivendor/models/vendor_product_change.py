import json
import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

# Content/price fields a vendor edit must route through admin approval.
# (Operational toggles like is_published / stock stay immediate.)
TRACKED_FIELDS = [
    ('name',             'Name'),
    ('list_price',       'Sale price'),
    ('standard_price',   'Cost'),
    ('description_sale', 'Sales description'),
    ('default_code',     'SKU'),
    ('barcode',          'Barcode'),
    ('weight',           'Weight'),
]
# Binary fields proposed but shown only as a flag in the diff.
BINARY_FIELDS = ['image_1920']


class VendorProductChange(models.Model):
    """A pending set of vendor-proposed edits to a product. The live product
    keeps its old values until an admin approves; then the proposed values are
    written. Gives admins a clean before/after to review."""
    _name = 'uellow.product.change'
    _description = 'Vendor Product Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one('product.template', string='Product',
        required=True, ondelete='cascade', index=True)
    vendor_id = fields.Many2one('uellow.vendor', string='Vendor',
        ondelete='set null', index=True)
    state = fields.Selection([
        ('pending',  'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending', index=True, copy=False)
    proposed_json = fields.Text('Proposed Values (JSON)', copy=False)
    change_summary = fields.Text('Changes', copy=False)
    submitted_by = fields.Many2one('res.users', string='Submitted By', ondelete='set null')
    submitted_date = fields.Datetime('Submitted On', default=fields.Datetime.now)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', ondelete='set null')
    reviewed_date = fields.Datetime('Reviewed On', copy=False)
    reject_reason = fields.Text('Reject Reason', copy=False)

    # ── build a human-readable before/after summary ──────────────────
    @api.model
    def _build_summary(self, product, vals):
        lines = []
        for fname, label in TRACKED_FIELDS:
            if fname in vals:
                old = product[fname]
                new = vals[fname]
                if (old or '') != (new or ''):
                    lines.append('%s: %s → %s' % (label, old if old not in (False, None) else '—', new))
        for fname in BINARY_FIELDS:
            if fname in vals:
                lines.append(_('Image updated'))
        if '__name_ar' in vals:
            old = product.with_context(lang='ar_001').name or '—'
            lines.append('%s: %s → %s' % (_('Name (AR)'), old, vals['__name_ar']))
        if '__public_categ_id' in vals:
            cat = self.env['product.public.category'].sudo().browse(vals['__public_categ_id'])
            lines.append('%s → %s' % (_('Category'), cat.name or vals['__public_categ_id']))
        if '__gallery' in vals:
            lines.append(_('%d gallery image(s) added') % len(vals['__gallery'] or []))
        return '\n'.join(lines) or _('(no visible change)')

    @api.model
    def submit_change(self, product, vals, user):
        """Create or merge a pending change for `product`. Returns the record.
        Does NOT touch the live product."""
        if not vals:
            return self.browse()
        existing = product.pending_change_id
        merged = {}
        if existing and existing.state == 'pending':
            try:
                merged = json.loads(existing.proposed_json or '{}')
            except (ValueError, TypeError):
                merged = {}
        merged.update(vals)
        summary = self._build_summary(product, merged)
        now = fields.Datetime.now()
        if existing and existing.state == 'pending':
            existing.write({
                'proposed_json': json.dumps(merged),
                'change_summary': summary,
                'submitted_by': user.id if user else False,
                'submitted_date': now,
            })
            rec = existing
        else:
            rec = self.create({
                'product_tmpl_id': product.id,
                'vendor_id': product.vendor_id.id,
                'proposed_json': json.dumps(merged),
                'change_summary': summary,
                'submitted_by': user.id if user else False,
                'submitted_date': now,
            })
            product.pending_change_id = rec.id
        rec._notify_admin()
        return rec

    def _notify_admin(self):
        self.ensure_one()
        p = self.product_tmpl_id
        p.message_post(body=_('🟠 Vendor edit submitted — under review:\n%s') % self.change_summary)
        try:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Vendor edit to approve — %s') % p.name,
                note=self.change_summary)
        except Exception:
            _logger.debug('activity schedule failed', exc_info=True)
        try:
            CN = self.env['mobile.customer.notification'].sudo()
            admins = CN._admin_partners()
            if admins:
                CN.push_role(
                    'notify_vendor_change', admins,
                    title_en='Product edit to approve',
                    title_ar='تعديل منتج بانتظار موافقتك',
                    body_en='%s edited %s.' % (self.vendor_id.display_name or '', p.name),
                    body_ar='%s عدّل %s.' % (self.vendor_id.display_name or '', p.name),
                    data={'type': 'product_change', 'id': self.id})
        except Exception:
            _logger.debug('admin change push failed', exc_info=True)

    def _notify_vendor(self, approved, reason=''):
        self.ensure_one()
        partner = (self.vendor_id.user_id.partner_id
                   if self.vendor_id and self.vendor_id.user_id else False)
        if not partner:
            return
        try:
            CN = self.env['mobile.customer.notification'].sudo()
            p = self.product_tmpl_id
            if approved:
                CN.push_role('notify_product_review', partner,
                    title_en='Edit approved',
                    title_ar='تم اعتماد التعديل',
                    body_en='Your changes to %s are now live.' % p.name,
                    body_ar='تم اعتماد تعديلاتك على %s.' % p.name,
                    data={'type': 'product_change', 'id': self.id})
            else:
                CN.push_role('notify_product_review', partner,
                    title_en='Edit rejected',
                    title_ar='تم رفض التعديل',
                    body_en='Your changes to %s were rejected. %s' % (p.name, reason or ''),
                    body_ar='تم رفض تعديلاتك على %s. %s' % (p.name, reason or ''),
                    data={'type': 'product_change', 'id': self.id})
        except Exception:
            _logger.debug('vendor change push failed', exc_info=True)

    # ── admin actions ────────────────────────────────────────────────
    def action_approve(self):
        for rec in self.filtered(lambda r: r.state == 'pending'):
            try:
                vals = json.loads(rec.proposed_json or '{}')
            except (ValueError, TypeError):
                vals = {}
            product = rec.product_tmpl_id.sudo()
            # special keys (applied separately from a plain write)
            name_ar = vals.pop('__name_ar', None)
            categ_id = vals.pop('__public_categ_id', None)
            gallery = vals.pop('__gallery', None)
            if vals:
                product.write(vals)
            if name_ar is not None:
                try:
                    product.with_context(lang='ar_001').write({'name': name_ar})
                except Exception:
                    _logger.debug('name_ar write failed', exc_info=True)
            if categ_id:
                try:
                    product.write({'public_categ_ids': [(4, int(categ_id))]})
                except Exception:
                    _logger.debug('category write failed', exc_info=True)
            if gallery:
                import base64
                for g in gallery:
                    try:
                        raw = base64.b64decode(g.split(',', 1)[-1])
                        self.env['product.image'].sudo().create({
                            'product_tmpl_id': product.id,
                            'name': product.name,
                            'image_1920': base64.b64encode(raw),
                        })
                    except Exception:
                        continue
            rec.write({
                'state': 'approved',
                'reviewed_by': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.product_tmpl_id.pending_change_id = False
            rec.product_tmpl_id.message_post(
                body=_('✅ Vendor edit approved and applied.'))
            rec._notify_vendor(approved=True)
            if rec.vendor_id:
                self.env['vendor.webhook'].dispatch(rec.vendor_id.id, 'product_approved', {
                    'product_id': rec.product_tmpl_id.id,
                    'name': rec.product_tmpl_id.name,
                })
        return True

    def action_reject(self):
        # opens nothing fancy — uses reject_reason already on the record if set
        for rec in self.filtered(lambda r: r.state == 'pending'):
            rec.write({
                'state': 'rejected',
                'reviewed_by': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            rec.product_tmpl_id.pending_change_id = False
            rec.product_tmpl_id.message_post(
                body=_('❌ Vendor edit rejected. %s') % (rec.reject_reason or ''))
            rec._notify_vendor(approved=False, reason=rec.reject_reason or '')
            if rec.vendor_id:
                self.env['vendor.webhook'].dispatch(rec.vendor_id.id, 'product_rejected', {
                    'product_id': rec.product_tmpl_id.id,
                    'name': rec.product_tmpl_id.name,
                    'reason': rec.reject_reason or '',
                })
        return True
