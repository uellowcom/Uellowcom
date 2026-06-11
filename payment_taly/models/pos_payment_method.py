# -*- coding: utf-8 -*-
"""
Taly as a POS payment terminal (v2.2.27)
========================================
Lets a cashier charge via Taly and FINISH the sale from the POS:
the POS creates an in-store checkout session → Taly SMSes the customer a
secure payment link (valid 15 min) → the customer pays on their phone →
the POS polls the order status and validates the payment on CONFIRMED.

All API work is delegated to the payment.provider (code 'taly'); this model
only exposes two thin RPC entry points for the POS UI.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        # POS terminal selection is a computed list, not a static Selection —
        # extend it the same way the core terminals (paytm/razorpay) do.
        return super()._get_payment_terminal_selection() + [('taly', 'Taly — أقساط')]

    taly_provider_id = fields.Many2one(
        'payment.provider', string='Taly Provider',
        domain=[('code', '=', 'taly')],
        help='The Taly payment provider used to open in-store sessions. '
             'Leave empty to auto-pick the enabled Taly provider.',
    )

    def _taly_provider(self):
        self.ensure_one()
        prov = self.taly_provider_id
        if not prov:
            prov = self.env['payment.provider'].sudo().search(
                [('code', '=', 'taly'), ('state', 'in', ('enabled', 'test'))],
                limit=1)
        return prov

    # ── RPC entry points called from the POS UI ──────────────────────────
    @api.model
    def taly_pos_create_session(self, method_id, order):
        """order: {reference, amount, currency, language, first_name,
        last_name, email, phone}. Returns the in-store session dict or
        {error}."""
        method = self.browse(method_id)
        prov = method._taly_provider()
        if not prov:
            return {'error': 'Taly provider is not configured / enabled.'}
        try:
            return prov._taly_create_instore_session({
                'merchant_order_id': order.get('reference'),
                'amount':     order.get('amount'),
                'currency':   order.get('currency') or 'KWD',
                'language':   order.get('language') or 'ar',
                'first_name': order.get('first_name'),
                'last_name':  order.get('last_name'),
                'email':      order.get('email'),
                'phone':      order.get('phone'),
                'redirect_url': prov.get_base_url(),
            })
        except Exception as e:
            _logger.warning('taly pos session failed: %s', e)
            return {'error': str(e)}

    @api.model
    def taly_pos_poll(self, method_id, merchant_order_id):
        """Returns {state: 'done'|'pending'|'cancel'|'', raw: '<TALY_STATUS>'}."""
        method = self.browse(method_id)
        prov = method._taly_provider()
        if not prov:
            return {'state': '', 'raw': 'no-provider'}
        try:
            state, raw = prov._taly_order_status(merchant_order_id)
            return {'state': state, 'raw': raw}
        except Exception as e:
            return {'state': '', 'raw': str(e)}
