from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    custom_mode = fields.Selection(related='provider_id.custom_mode')

    def action_collect(self):
        for rec in self.filtered(lambda tx: tx.state == 'pending'):
            rec.write({
                'state': 'done'
            })
