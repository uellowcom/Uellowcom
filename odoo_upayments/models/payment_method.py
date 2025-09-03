from odoo import fields, models, api


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    is_upayment_method = fields.Boolean('Is UPayment Method', default=False)
