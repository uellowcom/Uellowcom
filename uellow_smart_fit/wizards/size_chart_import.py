import base64
import csv
import io
import logging

from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Recognised CSV columns (case-insensitive, both EN and AR accepted).
FIELD_ALIASES = {
    'product':     'product_name',
    'product_name': 'product_name',
    'منتج':         'product_name',
    'name':         'product_name',
    'size':         'size_label',
    'size_label':   'size_label',
    'مقاس':         'size_label',
    'chest':        'chest_cm',
    'صدر':          'chest_cm',
    'shoulder':     'shoulder_cm',
    'كتف':          'shoulder_cm',
    'sleeve':       'sleeve_cm',
    'كم':           'sleeve_cm',
    'length':       'length_cm',
    'طول':          'length_cm',
    'waist':        'waist_cm',
    'وسط':          'waist_cm',
    'hip':          'hip_cm',
    'ورك':          'hip_cm',
    'inseam':       'inseam_cm',
    'ساق':          'inseam_cm',
    'thigh':        'thigh_cm',
    'فخذ':          'thigh_cm',
    'foot':         'foot_length_cm',
    'foot_length':  'foot_length_cm',
    'قدم':          'foot_length_cm',
    'tolerance':    'tolerance_cm',
    'تفاوت':        'tolerance_cm',
}

NUMERIC_FIELDS = {
    'chest_cm', 'shoulder_cm', 'sleeve_cm', 'length_cm',
    'waist_cm', 'hip_cm', 'inseam_cm', 'thigh_cm',
    'foot_length_cm', 'tolerance_cm',
}


class SizeChartImportWizard(models.TransientModel):
    _name = 'product.size.chart.import.wizard'
    _description = 'Import Product Size Charts from CSV/Excel'

    csv_file     = fields.Binary(string='CSV file', required=True)
    csv_filename = fields.Char(string='File name')
    update_existing = fields.Boolean(
        string='Update existing sizes', default=True,
        help='If a (product + size) row already exists, update its values instead of skipping.',
    )
    result_summary = fields.Text(string='Result', readonly=True)

    def action_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError(_('Please upload a CSV file first.'))

        try:
            raw = base64.b64decode(self.csv_file)
        except Exception as e:
            raise UserError(_('Could not decode the file: %s') % e)

        text = None
        for enc in ('utf-8-sig', 'utf-8', 'cp1256', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise UserError(_('Unsupported file encoding. Please save it as UTF-8.'))

        # Detect delimiter
        try:
            dialect = csv.Sniffer().sniff(text[:1024], delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(text), dialect)

        rows = list(reader)
        if len(rows) < 2:
            raise UserError(_('The file is empty or has no data rows.'))

        header = [c.strip().lower() for c in rows[0]]
        # Map headers to internal field names
        col_map = {}
        for idx, h in enumerate(header):
            key = FIELD_ALIASES.get(h)
            if key:
                col_map[idx] = key

        if 'product_name' not in col_map.values():
            raise UserError(_('Missing the product name column (product / product_name / منتج).'))
        if 'size_label' not in col_map.values():
            raise UserError(_('Missing the size column (size / size_label / مقاس).'))

        Product = self.env['product.template'].sudo()
        Chart   = self.env['product.size.chart'].sudo()

        created = updated = skipped = unmatched = 0
        errors  = []

        for row_no, row in enumerate(rows[1:], start=2):
            if not any((c or '').strip() for c in row):
                continue
            data = {}
            for idx, key in col_map.items():
                if idx >= len(row):
                    continue
                val = (row[idx] or '').strip()
                if not val:
                    continue
                if key in NUMERIC_FIELDS:
                    try:
                        data[key] = float(val.replace(',', '.'))
                    except ValueError:
                        errors.append(_('Row %d: %s value is not numeric: "%s"') % (row_no, key, val))
                        continue
                else:
                    data[key] = val

            pname = data.pop('product_name', '').strip()
            size  = data.pop('size_label', '').strip()
            if not pname or not size:
                skipped += 1
                continue

            product = Product.search([('name', '=ilike', pname)], limit=1)
            if not product:
                product = Product.search([('name', 'ilike', pname)], limit=1)
            if not product:
                unmatched += 1
                errors.append(_('Row %d: no product found with name "%s".') % (row_no, pname))
                continue

            existing = Chart.search([
                ('product_id', '=', product.id),
                ('size_label', '=ilike', size),
            ], limit=1)
            data['product_id'] = product.id
            data['size_label'] = size

            if existing:
                if self.update_existing:
                    existing.write(data)
                    updated += 1
                else:
                    skipped += 1
            else:
                Chart.create(data)
                created += 1

        summary = _(
            "✓ Done:\n"
            "  • Created: %d\n"
            "  • Updated: %d\n"
            "  • Skipped: %d\n"
            "  • No matching product: %d\n"
        ) % (created, updated, skipped, unmatched)
        if errors:
            summary += _('\n— Error details —\n') + '\n'.join(errors[:20])
            if len(errors) > 20:
                summary += _('\n... and more errors (%d total)') % len(errors)

        self.result_summary = summary
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_template(self):
        """Return a CSV template attachment for download."""
        sample = (
            'product_name,size,chest,shoulder,sleeve,length,waist,hip,inseam,thigh,foot_length,tolerance\n'
            'Test T-Shirt,S,96,43,21,68,86,96,,,,0\n'
            'Test T-Shirt,M,102,45,22,70,92,102,,,,0\n'
            'Test T-Shirt,L,108,47,23,72,98,108,,,,0\n'
        )
        attachment = self.env['ir.attachment'].sudo().create({
            'name':     'size_chart_template.csv',
            'type':     'binary',
            'datas':    base64.b64encode(sample.encode('utf-8')),
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
