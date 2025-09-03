from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    unique_token = fields.Char(readonly=True)
    token = fields.Char('Token')
    card_number = fields.Char('Card Number')
