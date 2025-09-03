from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PaymentRefundWizard(models.TransientModel):
    _inherit = 'payment.refund.wizard'

    total_paid_in_kwd = fields.Float('Total Paid In KWD', compute='_compute_total_amount_paid_in_kwd')
    # refund_amount_in_kwd = fields.Float('Refund Amount In KWD', compute='_compute_refund_amount_in_kwd')

    @api.depends('payment_id')
    def _compute_total_amount_paid_in_kwd(self):
        for rec in self:
            rec.total_paid_in_kwd = 0.0
            transaction = rec.payment_id.payment_transaction_id if rec.payment_id else None
            if transaction:
                if not transaction.upayment_verified:
                    raise ValidationError(
                        _('Please verify the payment of the order first.'
                          '\nTo verify the payment, go to the payment transaction.')
                    )
                if transaction.upayment_verified == 'failed':
                    raise ValidationError(_('Payment transaction failed. Refund is not allowed.'))
                rec.total_paid_in_kwd = transaction.total_paid_non_kwd or 0.0

    # @api.depends('amount_to_refund')
    # def _compute_refund_amount_in_kwd(self):
    #     refund_currency_id = self.env['res.currency'].sudo().search([('name', '=', 'KWD')], limit=1)
    #     if not refund_currency_id:
    #         raise ValidationError(_("Please activate the 'KWD' currency."))
    #     for rec in self:
    #         rec.refund_amount_in_kwd = 0.0
    #         if rec.amount_to_refund:
    #             rec.refund_amount_in_kwd = rec.currency_id._convert(
    #                 rec.amount_to_refund,
    #                 refund_currency_id,
    #                 rec.env.company,
    #                 fields.Date.today()
    #             )
