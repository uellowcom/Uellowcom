# -*- coding: utf-8 -*-
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    taly_order_id = fields.Char(string='Taly Order ID', readonly=True)
    taly_order_token = fields.Char(string='Taly Order Token', readonly=True)
    taly_order_status = fields.Char(string='Taly Status', readonly=True)
    taly_checkout_url = fields.Char(string='Checkout URL', readonly=True)
    taly_installment_plan = fields.Char(string='Installment Plan', readonly=True)
    taly_down_payment = fields.Float(string='Down Payment', readonly=True)
    taly_refunded_amount = fields.Float(string='Refunded Amount', default=0.0)
    taly_refund_reason = fields.Char(string='Refund Reason')
    taly_raw_response = fields.Text(string='Raw API Response', readonly=True)

    # ── Rendering (redirect to Taly) ─────────────────────────────────────────

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'taly':
            return res

        provider = self.provider_id
        try:
            checkout_url, order_id, order_token = provider._taly_create_order(self)
            self.sudo().write({
                'taly_order_id': order_id,
                'taly_order_token': order_token,
                'taly_checkout_url': checkout_url,
            })
            res.update({
                'checkout_url': checkout_url,
                'taly_order_id': order_id,
                'provider_name': 'Taly',
            })
        except Exception as e:
            _logger.error("Taly: failed to create order for tx %s: %s", self.reference, e)
            raise ValidationError(
                _("تعذّر الاتصال بشركة تالي. يرجى المحاولة لاحقاً.\n%s") % str(e)
            )
        return res

    # ── Notification processing ───────────────────────────────────────────────

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'taly' or len(tx) == 1:
            return tx

        ref = (
            notification_data.get('merchantOrderId')
            or notification_data.get('reference')
            or notification_data.get('order_reference')
        )
        if ref:
            tx = self.search([
                ('reference', '=', ref),
                ('provider_code', '=', 'taly'),
            ], limit=1)

        if not tx:
            order_token = notification_data.get('orderToken')
            if order_token:
                tx = self.search([
                    ('taly_order_token', '=', order_token),
                    ('provider_code', '=', 'taly'),
                ], limit=1)

        if not tx:
            raise ValidationError(
                _("Taly: لا توجد معاملة للمرجع: %s") % (ref or 'unknown')
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'taly':
            return

        from .payment_provider import TALY_ORDER_STATUSES

        raw_status = (
            notification_data.get('orderStatus')
            or notification_data.get('status')
            or ''
        ).upper()

        self.sudo().write({
            'taly_order_status': raw_status,
            'taly_raw_response': json.dumps(notification_data, ensure_ascii=False, indent=2),
            'taly_order_token': notification_data.get('orderToken') or self.taly_order_token,
        })

        odoo_state = TALY_ORDER_STATUSES.get(raw_status)

        if odoo_state == 'done':
            self._set_done()
        elif odoo_state == 'pending':
            self._set_pending()
        elif odoo_state == 'cancel':
            self._set_canceled()
        else:
            _logger.warning(
                "Taly: unknown status '%s' for tx %s — keeping current state",
                raw_status, self.reference,
            )

    # ── Manual sync from backend ──────────────────────────────────────────────

    def action_taly_sync_status(self):
        self.ensure_one()
        if self.provider_code != 'taly':
            raise ValidationError(_("This action is only for Taly transactions."))
        if not self.taly_order_token:
            raise ValidationError(_("لا يوجد Order Token لهذه المعاملة."))
        try:
            data = self.provider_id._taly_get_order(self.taly_order_token)
            self._process_notification_data(data)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Taly Sync'),
                    'message': _('تم تحديث الحالة: %s') % self.taly_order_status,
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            raise ValidationError(_("فشل تحديث الحالة: %s") % str(e))

    def action_taly_refund(self):
        self.ensure_one()
        if self.provider_code != 'taly':
            raise ValidationError(_("This action is only for Taly transactions."))
        return {
            'name': _('Taly Refund'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.taly.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_transaction_id': self.id,
                'default_amount': self.amount - self.taly_refunded_amount,
            },
        }

    def action_open_taly_checkout(self):
        self.ensure_one()
        if not self.taly_checkout_url:
            raise ValidationError(_("لا يوجد رابط دفع لهذه المعاملة."))
        return {
            'type': 'ir.actions.act_url',
            'url': self.taly_checkout_url,
            'target': 'new',
        }
