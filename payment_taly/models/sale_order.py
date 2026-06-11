# -*- coding: utf-8 -*-
"""
Taly charge for the mobile app's native checkout (v2.2.27)
=========================================================
The app posts the order then expects a `payment_url` to open in a webview.
For Taly we create a real payment.transaction linked to the sale order and
return its Taly secure-checkout URL. When the customer pays, the Taly
webhook/return drives the tx to `done` and Odoo's STANDARD payment→sale flow
confirms the order automatically (no bespoke capture pipeline needed).
"""
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _taly_mobile_charge(self, lang='ar'):
        """Create a Taly transaction for THIS order (delivery line already
        added by the caller) and return the secure checkout URL."""
        self.ensure_one()
        provider = self.env['payment.provider'].sudo().search(
            [('code', '=', 'taly'), ('state', 'in', ('enabled', 'test'))],
            limit=1)
        if not provider:
            raise UserError(_('Taly is not configured / enabled.'))
        method = self.env['payment.method'].sudo().search(
            [('code', '=', 'taly')], limit=1)
        Tx = self.env['payment.transaction'].sudo()
        reference = Tx._compute_reference(provider.code, prefix=(self.name or 'SO'))
        tx = Tx.create({
            'provider_id': provider.id,
            'payment_method_id': method.id if method else False,
            'amount': round(self.amount_total or 0.0, 3),
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'reference': reference,
            'sale_order_ids': [(6, 0, [self.id])],
        })
        rendering = tx._get_specific_rendering_values({})
        url = rendering.get('checkout_url') or tx.taly_checkout_url
        if not url:
            raise UserError(_('Taly did not return a checkout URL.'))
        return url
