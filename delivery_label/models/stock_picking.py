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

    payment_reference = fields.Char(string='Payment Reference', copy=False)
    payment_provider_name = fields.Char(string='Payment Provider', copy=False)
    paid_on = fields.Datetime(string='Paid On', copy=False)

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
        for picking in pickings:
            try:
                picking._uc_sync_payment()
            except Exception:
                pass
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

    def _uc_order_is_paid(self, so):
        if not so:
            return False
        if getattr(so, 'upayments_paid', False):
            return True
        # An online (non-COD) payment transaction that reached done/authorized
        # means the customer already paid (Taly, UPayments, cards ...), even
        # when no invoice exists yet to reconcile against. This is the reliable
        # signal at picking-creation time (the tx is 'done' before the SO is
        # confirmed), and it prevents a driver collecting cash for a paid order.
        try:
            cod_provider = self.env.ref('ms_payment_cod.payment_provider_cod',
                                        raise_if_not_found=False)
            cod_pid = cod_provider.id if cod_provider else 0
            if so.transaction_ids.filtered(
                    lambda t: t.state in ('done', 'authorized')
                    and t.provider_id.id != cod_pid
                    and (t.provider_id.code or '') != 'cod'):
                return True
        except Exception:
            pass
        try:
            if so.amount_total > 0 and getattr(so, 'amount_unpaid', so.amount_total) <= 0.001:
                return True
        except Exception:
            pass
        return bool(so.invoice_ids.filtered(lambda i: i.payment_state in ('paid', 'in_payment')))

    def _uc_sync_payment(self, order=None):
        """Flip the picking to PAID (with provider + reference) once its order is
        actually paid online; leave COD orders as COD."""
        for pk in self:
            so = order or pk._get_related_sale_order()
            if not so or not pk._uc_order_is_paid(so):
                continue
            tx = so.transaction_ids.sorted('id')[-1:] if so.transaction_ids else so.env['payment.transaction']
            ref = (getattr(so, 'upayments_track_id', '') or
                   ((tx.provider_reference or tx.reference) if tx else '') or '')
            prov = ((tx.provider_id.name if tx and tx.provider_id else '') or
                    ('UPayments' if getattr(so, 'upayments_paid', False) else 'Online'))
            pk.write({
                'payment_method': 'paid',
                'payment_reference': ref or pk.payment_reference,
                'payment_provider_name': prov,
                'paid_on': pk.paid_on or fields.Datetime.now(),
            })

    def get_location_qr_url(self):
        """Google-Maps URL for the delivery location, used as the QR payload so
        scanning the label opens the customer's address straight in Maps."""
        self.ensure_one()
        import urllib.parse
        so = self._get_related_sale_order()
        # 1) the order's computed Google-Maps link (lat/lng or address fallback)
        if so and getattr(so, 'delivery_gmaps_url', False):
            return so.delivery_gmaps_url
        # 2) the order's saved GPS pin
        if so and getattr(so, 'delivery_lat', 0) and getattr(so, 'delivery_lng', 0):
            return ('https://www.google.com/maps/search/?api=1&query=%s,%s'
                    % (so.delivery_lat, so.delivery_lng))
        # 3) the picking partner's saved GPS pin
        p = self.partner_id
        if p and (p.partner_latitude or p.partner_longitude):
            return ('https://www.google.com/maps/search/?api=1&query=%s,%s'
                    % (p.partner_latitude, p.partner_longitude))
        # 4) build a text query from the address
        if p:
            bits = [p.street, p.street2, p.city,
                    p.country_id.name if p.country_id else '']
            addr = ', '.join([b for b in bits if b])
            if addr:
                return ('https://www.google.com/maps/search/?api=1&query=%s'
                        % urllib.parse.quote(addr))
        return ''

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

