# -*- coding: utf-8 -*-
import base64
from odoo import api, models


class ReportSaleReceipt(models.AbstractModel):
    _name = 'report.uellow_order_prep.report_sale_receipt'
    _description = 'Uellow Sales Receipt'

    @api.model
    def _get_report_values(self, docids, data=None):
        orders = self.env['sale.order'].browse(docids)
        # Pre-render the Code128 barcode inline as a data-uri — fetching
        # /report/barcode/… from wkhtmltopdf is unreliable, so embed it.
        barcodes = {}
        for o in orders:
            try:
                png = self.env['ir.actions.report'].barcode(
                    'Code128', o.name or '', width=600, height=110)
                barcodes[o.id] = 'data:image/png;base64,%s' % base64.b64encode(png).decode()
            except Exception:
                barcodes[o.id] = ''
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': orders,
            'barcodes': barcodes,
        }
