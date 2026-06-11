# -*- coding: utf-8 -*-
"""v2.2.33 — COD → online auto-conversion.

When a Cash-on-Delivery order is paid online (customer pays via the app, a
driver pay-link, or any payment.transaction) BEFORE it is delivered, the
order should stop being a cash collection: it flips to 'online' so the
driver no longer has to collect cash and the carrier cash ledger stays clean.
"""
from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _set_done(self, *args, **kwargs):
        res = super()._set_done(*args, **kwargs)
        try:
            self._carrier_convert_cod_orders()
        except Exception:
            # never break the payment flow on the dispatch side-write
            pass
        return res

    def _carrier_convert_cod_orders(self):
        for tx in self:
            for order in tx.sale_order_ids:
                if (getattr(order, 'payment_method_type', None) == 'cash'
                        and order.delivery_status not in (
                            'delivered', 'failed', 'failed_returned')):
                    order.sudo().write({
                        'payment_method_type': 'online',
                        'cash_collection_status': 'not_applicable',
                    })
                    order.message_post(
                        body='💳 Paid online before delivery — converted from '
                             'Cash on Delivery to Online Payment.')
