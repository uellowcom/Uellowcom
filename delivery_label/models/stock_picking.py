# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    payment_method = fields.Selection([
        ('cod', 'COD - Cash on Delivery'),
        ('paid', 'PAID'),
    ], string='Payment Method', default='cod', copy=True)

    cod_amount = fields.Monetary(
        string='COD Amount',
        currency_field='currency_id',
        copy=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        pickings = super().create(vals_list)
        for picking, vals in zip(pickings, vals_list):
            if picking.payment_method == 'cod' and not vals.get('cod_amount') and not picking.cod_amount:
                picking.cod_amount = picking._get_cod_amount_from_related_document()
        return pickings

    def write(self, vals):
        result = super().write(vals)
        trigger_fields = {'payment_method', 'origin', 'partner_id', 'sale_id'}
        if 'cod_amount' not in vals and trigger_fields.intersection(vals):
            for picking in self:
                if picking.payment_method == 'cod' and not picking.cod_amount:
                    amount = picking._get_cod_amount_from_related_document()
                    if amount:
                        picking.cod_amount = amount
        return result

    @api.onchange('payment_method', 'origin', 'partner_id')
    def _onchange_cod_amount_from_related_document(self):
        for picking in self:
            if picking.payment_method == 'cod' and not picking.cod_amount:
                picking.cod_amount = picking._get_cod_amount_from_related_document()

    def _get_related_sale_order(self):
        self.ensure_one()
        SaleOrder = self.env['sale.order']
        if 'sale_id' in self._fields and self.sale_id:
            return self.sale_id
        if self.origin:
            for origin in [part.strip() for part in self.origin.split(',') if part.strip()]:
                sale_order = SaleOrder.search([('name', '=', origin)], limit=1)
                if sale_order:
                    return sale_order
        return SaleOrder.browse()

    def _get_cod_amount_from_related_document(self):
        self.ensure_one()
        sale_order = self._get_related_sale_order()
        if not sale_order:
            return 0.0
        if 'invoice_ids' in sale_order._fields and sale_order.invoice_ids:
            invoices = sale_order.invoice_ids.filtered(lambda invoice: invoice.state != 'cancel')
            if 'move_type' in invoices._fields:
                invoices = invoices.filtered(lambda invoice: invoice.move_type in ('out_invoice', 'out_refund'))
            posted_invoices = invoices.filtered(lambda invoice: invoice.state == 'posted')
            invoice = (posted_invoices or invoices).sorted(lambda invoice: (invoice.invoice_date or invoice.date or fields.Date.today(), invoice.id), reverse=True)[:1]
            if invoice:
                return invoice.amount_residual or invoice.amount_total or 0.0
        return sale_order.amount_total or 0.0

    def get_barcode_b64(self, value, barcode_type='Code128', width=300, height=40):
        if not value:
            return ''
        try:
            raw = self.env['ir.actions.report'].barcode(
                barcode_type, str(value), width=width, height=height, humanreadable=False
            )
            return base64.b64encode(raw).decode()
        except Exception:
            _logger.exception("Unable to generate barcode for delivery label")
            return ''

    def get_barcode_vertical_b64(self, value):
        if not value:
            return ''
        try:
            from PIL import Image

            raw = self.env['ir.actions.report'].barcode(
                'Code128', str(value), width=300, height=40, humanreadable=False
            )
            img = Image.open(io.BytesIO(raw))
            img_rotated = img.rotate(90, expand=True)
            buffer = io.BytesIO()
            img_rotated.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode()
        except Exception:
            _logger.exception("Unable to generate vertical barcode for delivery label")
            return self.get_barcode_b64(value, width=40, height=200)

    def print_delivery_label(self):
        self.ensure_one()
        return self.env.ref('delivery_label.action_report_delivery_label').report_action(self)

