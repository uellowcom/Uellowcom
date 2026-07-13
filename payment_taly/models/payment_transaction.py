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
    # Human-readable, bilingual auto-diagnosis shown under each record so any
    # future failure is self-explanatory to whoever opens the transaction.
    taly_diagnosis = fields.Text(
        string='Diagnosis / التشخيص', readonly=True,
        help='Auto-generated explanation of the current Taly status and the '
             'recommended action. Refreshed on every status sync.')

    # Map of Taly status -> bilingual (English first) diagnosis + action.
    _TALY_DIAGNOSIS = {
        'DONE': "✅ Paid successfully — order confirmed. / تم الدفع بنجاح — الطلب مؤكَّد.",
        'PENDING': "⏳ Awaiting the customer to finish paying at Taly. The reconcile "
                   "cron re-checks every 15 min; nothing to do unless it stays stuck. "
                   "/ بانتظار إتمام العميل للدفع لدى تالي. كرون المطابقة يعيد الفحص كل "
                   "١٥ دقيقة؛ لا إجراء مطلوب إلا إذا بقي عالقاً.",
        'INCOMPLETED': "⚠️ The customer opened the Taly page but did NOT complete "
                       "verification/payment (abandoned, failed the OTP, or has no "
                       "eligible Taly account). No money was taken. Fix: make sure the "
                       "phone is a SINGLE valid Kuwaiti number, then ask the customer to "
                       "retry or use another method. / فتح العميل صفحة تالي ولم يُكمل "
                       "التحقق/الدفع (تراجع، فشل رمز التحقق، أو لا يملك حساباً مؤهّلاً في "
                       "تالي). لم يُخصم أي مبلغ. الحل: تأكد أن الهاتف رقم كويتي واحد صحيح، "
                       "ثم اطلب من العميل إعادة المحاولة أو استخدام وسيلة دفع أخرى.",
        'REJECTED': "❌ Taly DECLINED the installment (Taly's own credit/eligibility "
                    "decision). This is NOT a system error and cannot be overridden from "
                    "our side — offer the customer another payment method. / رفضت تالي "
                    "التقسيط (قرار ائتماني/أهلية من تالي نفسها). ليس خطأ في النظام ولا "
                    "يمكن تجاوزه من جهتنا — اعرض على العميل وسيلة دفع أخرى.",
        'CANCELLED': "🚫 Cancelled or the 15-min payment window expired before completion. "
                     "/ أُلغي الطلب أو انتهت نافذة الدفع (١٥ دقيقة) قبل الإتمام.",
        'REFUNDED': "↩️ Refunded. / تم استرداد المبلغ.",
        '': "ℹ️ No status from Taly yet — the order may not have been created, or it is "
            "awaiting the first sync. / لا توجد حالة من تالي بعد — قد لا يكون الطلب أُنشئ، "
            "أو بانتظار أول مزامنة.",
    }

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
            or notification_data.get('paymentStatus')
            or notification_data.get('finalStatus')
            or ''
        ).upper()

        self.sudo().write({
            'taly_order_status': raw_status,
            'taly_raw_response': json.dumps(notification_data, ensure_ascii=False, indent=2),
            'taly_order_token': notification_data.get('orderToken') or self.taly_order_token,
        })

        odoo_state = TALY_ORDER_STATUSES.get(raw_status)

        # Write the human diagnosis BEFORE changing state so it's always present.
        self.sudo().write({'taly_diagnosis': self._taly_build_diagnosis(raw_status)})

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

    def _taly_build_diagnosis(self, raw_status=None):
        """Return a bilingual, human-readable explanation of the current Taly
        status + recommended action, with a phone-quality warning appended when
        the customer's phone holds more than one number."""
        self.ensure_one()
        from .payment_provider import TALY_ORDER_STATUSES
        raw = (raw_status or self.taly_order_status or '').upper()
        odoo_state = TALY_ORDER_STATUSES.get(raw)
        if odoo_state == 'done':
            key = 'DONE'
        elif odoo_state == 'pending':
            key = 'PENDING'
        elif raw == 'INCOMPLETED':
            key = 'INCOMPLETED'
        elif raw in ('REJECTED', 'FAILED', 'FAILURE'):
            key = 'REJECTED'
        elif raw in ('CANCELLED', 'CANCEL', 'EXPIRED'):
            key = 'CANCELLED'
        elif raw == 'REFUNDED':
            key = 'REFUNDED'
        elif not raw:
            key = ''
        else:
            key = None
        text = self._TALY_DIAGNOSIS.get(key) if key is not None else (
            "ℹ️ Taly status: %s (unmapped) — review manually. / حالة تالي: %s "
            "(غير مصنّفة) — تُراجع يدوياً." % (raw, raw))

        # Phone-quality guard: a mashed "num1/num2" phone is the #1 cause of
        # INCOMPLETED (the verification SMS can't be delivered).
        import re as _re
        groups = [g for g in _re.split(r'[\/,;|]+', self.partner_id.phone or '')
                  if len(_re.sub(r'\D', '', g)) >= 7]
        if len(groups) >= 2:
            text += ("\n📵 The customer phone holds MORE THAN ONE number "
                     "(%s) — correct it to a single number. / رقم هاتف العميل "
                     "يحتوي أكثر من رقم (%s) — صحّحه إلى رقم واحد."
                     % (self.partner_id.phone, self.partner_id.phone))
        return text

    # ── Authoritative status pull (anti-forgery) ──────────────────────────────

    def _taly_pull_status(self):
        """Fetch the order status straight from Taly (server-to-server) and
        process it. This is the TRUSTED path: the webhook + the customer
        redirect both call this instead of believing the posted status, so a
        forged 'success' webhook can never mark an order paid."""
        self.ensure_one()
        data = self.provider_id._taly_get_order(self.reference)
        self._process_notification_data(data)
        return data

    # ── Safety-net reconcile cron ─────────────────────────────────────────────

    @api.model
    def _cron_taly_reconcile(self, days=14, limit=200):
        """Pull authoritative status from Taly for every still-open Taly
        transaction and process it.

        Taly's async webhook is best-effort and the customer browser-redirect
        only fires if they come back — so without this an order the customer
        actually PAID can sit in 'draft' forever (money received, order never
        confirmed). This server-to-server poll closes that gap: it confirms any
        order Taly reports CONFIRMED/PAID and cancels REJECTED/EXPIRED ones."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=days)
        txs = self.sudo().search([
            ('provider_code', '=', 'taly'),
            ('state', 'in', ('draft', 'pending')),
            ('create_date', '>=', cutoff),
            ('taly_order_id', '!=', False),
        ], order='create_date desc', limit=limit)
        for tx in txs:
            try:
                tx._taly_pull_status()
                # commit per-tx so one bad order can't roll back the batch
                self.env.cr.commit()
            except Exception as e:
                _logger.warning("Taly reconcile: tx %s failed: %s", tx.reference, e)
                self.env.cr.rollback()
        return True

    # ── Manual sync from backend ──────────────────────────────────────────────

    def action_taly_sync_status(self):
        self.ensure_one()
        if self.provider_code != 'taly':
            raise ValidationError(_("This action is only for Taly transactions."))
        if not self.reference:
            raise ValidationError(_("لا يوجد مرجع لهذه المعاملة."))
        try:
            # get-order is keyed by the MERCHANT order id (our reference).
            self._taly_pull_status()
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
