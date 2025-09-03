from odoo import fields, models, http, _
from odoo.exceptions import ValidationError


class PaymentProviderCodRule(models.Model):
    _name = "payment.provider.cod.rule"
    _description = "Payment Provider COD Rules"
    _rec_name = "pricing_based"

    provider_id = fields.Many2one(
        comodel_name='payment.provider',
        string='Provider',
        ondelete='cascade')
    pricing_based = fields.Selection(
        string='Pricing Based on',
        selection=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage'),
        ], required=True,
    )
    fixed_amount = fields.Monetary(
        string='Fee Amount',
        currency_field='company_currency_id',
        required=False)
    percentage_amount = fields.Float(
        string='Fee (%)',
        digits='Product Price',
        required=False)
    min_amount = fields.Monetary(
        string='Min Amount',
        currency_field='company_currency_id',
        required=False)
    max_amount = fields.Monetary(
        string='Max Amount',
        currency_field='company_currency_id',
        required=False)
    company_currency_id = fields.Many2one(
        string="Currency",
        related='provider_id.company_id.currency_id',
        help='Amount will be converted to customer currency.'
    )
    sequence = fields.Integer(
        string='Sequence',
        required=False)
