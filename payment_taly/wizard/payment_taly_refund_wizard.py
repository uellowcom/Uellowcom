# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PaymentTalyRefundWizard(models.TransientModel):
    _name = 'payment.taly.refund.wizard'
    _description = 'Taly Refund Wizard'

    transaction_id = fields.Many2one(
        'payment.transaction',
        string='Transaction',
        required=True,
        readonly=True,
    )
    amount = fields.Float(string='Refund Amount', required=True)
    max_amount = fields.Float(
        string='Max Refundable',
        compute='_compute_max_amount',
    )
    reason = fields.Char(string='Refund Reason', required=True, default='Customer request')
    currency_id = fields.Many2one(
        related='transaction_id.currency_id',
        string='Currency',
    )

    @api.depends('transaction_id')
    def _compute_max_amount(self):
        for rec in self:
            if rec.transaction_id:
                rec.max_amount = (
                    rec.transaction_id.amount - rec.transaction_id.taly_refunded_amount
                )
            else:
                rec.max_amount = 0.0

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("مبلغ الاسترداد يجب أن يكون أكبر من صفر."))
            if rec.amount > rec.max_amount:
                raise ValidationError(
                    _("مبلغ الاسترداد (%.3f) أكبر من الحد الأقصى الممكن (%.3f).")
                    % (rec.amount, rec.max_amount)
                )

    def action_confirm_refund(self):
        self.ensure_one()
        tx = self.transaction_id
        if tx.provider_code != 'taly':
            raise UserError(_("This wizard is only for Taly transactions."))
        if tx.state != 'done':
            raise UserError(_("يمكن الاسترداد فقط للمعاملات المكتملة."))
        if not tx.taly_order_token:
            raise UserError(_("لا يوجد Order Token لهذه المعاملة. يرجى التواصل مع تالي مباشرة."))

        try:
            result = tx.provider_id._taly_refund_order(
                order_token=tx.taly_order_token,
                amount=self.amount,
                reason=self.reason,
            )
            tx.sudo().write({
                'taly_refunded_amount': tx.taly_refunded_amount + self.amount,
                'taly_refund_reason': self.reason,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Taly Refund'),
                    'message': _('✅ تم طلب الاسترداد بنجاح: %.3f %s') % (
                        self.amount, tx.currency_id.name
                    ),
                    'type': 'success',
                    'sticky': False,
                },
            }
        except Exception as e:
            raise UserError(_("فشل طلب الاسترداد:\n%s") % str(e))
