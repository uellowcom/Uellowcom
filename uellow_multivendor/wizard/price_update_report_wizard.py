# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PriceUpdateReportWizard(models.TransientModel):
    """Builds the bilingual 'Update Prices' sheet a vendor reviews on paper:
    product image, name (EN+AR), barcode/code, current cost price, and a blank
    'New Price' column to hand-write. Outputs print/PDF or a real Excel file."""
    _name = 'uellow.price.report.wizard'
    _description = 'Vendor Update-Prices Report'

    vendor_id = fields.Many2one('uellow.vendor', string='Vendor / التاجر', required=True)
    category_id = fields.Many2one(
        'product.public.category', string='Category / القسم',
        help='Optional — limit to one website category.')
    only_published = fields.Boolean('Published only / المنشورة فقط', default=False)
    order_by = fields.Selection([
        ('name', 'Name / الاسم'),
        ('default_code', 'Code / الكود'),
        ('list_price desc', 'Price (high→low) / السعر تنازلي'),
    ], string='Sort / الترتيب', default='name')
    product_count = fields.Integer('Products', compute='_compute_count')

    @api.depends('vendor_id', 'category_id', 'only_published')
    def _compute_count(self):
        for w in self:
            w.product_count = len(w._products()) if w.vendor_id else 0

    def _products(self):
        self.ensure_one()
        domain = [('vendor_id', '=', self.vendor_id.id)]
        if self.only_published:
            domain.append(('is_published', '=', True))
        if self.category_id:
            domain.append(('public_categ_ids', 'child_of', self.category_id.id))
        return self.env['product.template'].search(domain, order=self.order_by or 'name')

    @staticmethod
    def _brand_of(product):
        """Brand label read from the Brand attribute (id=1) lines, else brand_id."""
        for line in product.attribute_line_ids:
            if line.attribute_id.id == 1 and line.value_ids:
                return line.value_ids[0].name
        return product.brand_id.name if product.brand_id else ''

    @api.model
    def _barcode_uri(self, code):
        """Self-contained Code128 barcode as a data-URI (wkhtmltopdf can't fetch
        the /report/barcode/ URL reliably in production)."""
        if not code:
            return ''
        try:
            png = self.env['ir.actions.report'].barcode(
                'Code128', code, width=600, height=120, humanreadable=0)
            return 'data:image/png;base64,%s' % base64.b64encode(png).decode()
        except Exception:
            return ''

    @staticmethod
    def _img_mime(b64):
        """Return (mime, b64) for a renderable raster (PNG/JPEG/GIF) or (None, b64)."""
        raw = base64.b64decode(b64)
        if raw[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png', b64
        if raw[:3] == b'\xff\xd8\xff':
            return 'image/jpeg', b64
        if raw[:6] in (b'GIF87a', b'GIF89a'):
            return 'image/gif', b64
        return None, b64

    @api.model
    def _img_uri(self, product):
        """Product thumbnail as a data-URI for the PDF. Prefer the main image if
        it's a renderable raster; if it's WebP (wkhtmltopdf can't render WebP),
        fall back to the pre-converted JPEG report thumbnail; else empty."""
        img = product.image_128
        if img:
            b64 = img.decode() if isinstance(img, bytes) else img
            mime, b64 = self._img_mime(b64)
            if mime:
                return 'data:%s;base64,%s' % (mime, b64)
        thumb = product.uc_report_thumb
        if thumb:
            b64 = thumb.decode() if isinstance(thumb, bytes) else thumb
            mime, b64 = self._img_mime(b64)
            if mime:
                return 'data:%s;base64,%s' % (mime, b64)
        return ''

    @api.model
    def _logo_uri(self):
        """Uellow logo embedded as a data-URI so the PDF never needs a network fetch.
        Prefer the company logo (PNG); the website logo is WebP which wkhtmltopdf
        (old WebKit) cannot render. Detect the real mime from magic bytes."""
        logo = self.env.company.logo or self.env['website'].browse(1).logo
        if not logo:
            return ''
        b64 = logo.decode() if isinstance(logo, bytes) else logo
        raw = base64.b64decode(b64)
        mime = 'image/png'
        if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
            mime = 'image/webp'
        elif raw[:3] == b'\xff\xd8\xff':
            mime = 'image/jpeg'
        return 'data:%s;base64,%s' % (mime, b64)

    def _report_data(self):
        return {
            'vendor_name': self.vendor_id.display_name or self.vendor_id.store_name_en or '',
            'vendor_name_ar': self.vendor_id.store_name_ar or '',
            'report_date': fields.Date.context_today(self).strftime('%d/%m/%Y'),
        }

    def action_print_pdf(self):
        self.ensure_one()
        products = self._products()
        if not products:
            raise UserError(_('No products found for this vendor with the selected filters.\n'
                              'لا توجد منتجات لهذا التاجر بالفلاتر المحددة.'))
        data = self._report_data()
        data['product_ids'] = products.ids   # parser rebuilds docs from this (robust)
        return self.env.ref('uellow_multivendor.action_report_price_update').report_action(
            products.ids, data=data)

    # ---- Excel export (xlsxwriter) ----
    def action_export_xlsx(self):
        self.ensure_one()
        products = self._products()
        if not products:
            raise UserError(_('No products found for this vendor with the selected filters.\n'
                              'لا توجد منتجات لهذا التاجر بالفلاتر المحددة.'))
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter is not available on the server.'))

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Update Prices')
        ws.right_to_left()

        yellow = '#F5C320'
        dark = '#412402'
        f_title = wb.add_format({'bold': True, 'font_size': 16, 'font_color': dark})
        f_meta = wb.add_format({'font_size': 10, 'font_color': '#666666'})
        f_head = wb.add_format({'bold': True, 'font_size': 10, 'bg_color': yellow,
                                'font_color': dark, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        f_cell = wb.add_format({'font_size': 10, 'border': 1, 'valign': 'vcenter', 'text_wrap': True})
        f_center = wb.add_format({'font_size': 10, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        f_cost = wb.add_format({'font_size': 10, 'border': 1, 'align': 'center', 'valign': 'vcenter',
                                'bold': True, 'num_format': '0.000', 'font_color': dark})
        f_new = wb.add_format({'font_size': 10, 'border': 1, 'bg_color': '#FFFDF4'})

        ws.set_column('A:A', 4)
        ws.set_column('B:B', 10)   # image
        ws.set_column('C:C', 16)   # code/barcode
        ws.set_column('D:D', 40)   # name en
        ws.set_column('E:E', 40)   # name ar
        ws.set_column('F:F', 14)   # brand
        ws.set_column('G:G', 12)   # cost
        ws.set_column('H:H', 16)   # new price

        data = self._report_data()
        ws.merge_range('A1:E1', 'uellow · UPDATE PRICES · تحديث الأسعار', f_title)
        ws.write('G1', 'Date / التاريخ:', f_meta)
        ws.write('H1', data['report_date'], f_meta)
        ws.merge_range('A2:E2', 'Vendor / التاجر: %s' % data['vendor_name'], f_meta)
        ws.write('G2', 'Items / المنتجات:', f_meta)
        ws.write('H2', len(products), f_meta)

        headers = ['#', 'Image\nالصورة', 'Barcode/Code\nالباركود', 'Product (EN)\nالمنتج',
                   'المنتج (AR)', 'Brand\nالبراند', 'Cost\nالتكلفة', 'Updated Price\nالسعر المُحدَّث']
        row = 3
        for col, h in enumerate(headers):
            ws.write(row, col, h, f_head)
        ws.set_row(row, 30)

        row = 4
        for idx, p in enumerate(products, 1):
            ws.set_row(row, 48)
            ws.write(row, 0, idx, f_center)
            # image — xlsxwriter supports PNG/JPEG/GIF/BMP only (NOT webp), so
            # check the magic bytes and skip unsupported formats to avoid crashing.
            ws.write(row, 1, '', f_center)
            for src in (p.image_128, p.uc_report_thumb):
                if not src:
                    continue
                try:
                    raw = base64.b64decode(src)
                    if raw[:8] == b'\x89PNG\r\n\x1a\n' or raw[:3] == b'\xff\xd8\xff' \
                       or raw[:6] in (b'GIF87a', b'GIF89a'):
                        ws.insert_image(row, 1, 'p%s.img' % p.id, {
                            'image_data': io.BytesIO(raw), 'x_scale': 0.45, 'y_scale': 0.45,
                            'object_position': 1, 'x_offset': 4, 'y_offset': 4})
                        break
                except Exception:
                    pass
            code = p.barcode or p.default_code or ''
            ws.write(row, 2, code, f_center)
            ws.write(row, 3, p.with_context(lang='en_US').name or '', f_cell)
            ws.write(row, 4, p.with_context(lang='ar_001').name or '', f_cell)
            ws.write(row, 5, self._brand_of(p), f_center)
            cost = p.standard_price or p.list_price or 0.0
            ws.write_number(row, 6, cost, f_cost)
            ws.write(row, 7, '', f_new)
            row += 1

        wb.close()
        buf.seek(0)
        fname = 'UpdatePrices_%s_%s.xlsx' % (
            (data['vendor_name'] or 'vendor').replace(' ', '_'), data['report_date'].replace('/', '-'))
        att = self.env['ir.attachment'].create({
            'name': fname,
            'datas': base64.b64encode(buf.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % att.id,
            'target': 'self',
        }


class PriceUpdateReportParser(models.AbstractModel):
    """Report parser — builds `docs` explicitly from the product ids passed in
    `data` so the printout NEVER comes out empty (passing docids + custom data
    through report_action can otherwise drop the records)."""
    _name = 'report.uellow_multivendor.report_price_update'
    _description = 'Update Prices Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        ids = data.get('product_ids') or docids or []
        docs = self.env['product.template'].browse(ids).exists()
        return {
            'doc_ids': docs.ids,
            'doc_model': 'product.template',
            'docs': docs,
            'data': data,
        }
