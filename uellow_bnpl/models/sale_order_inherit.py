from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bnpl_application_id = fields.Many2one(
        'uellow.bnpl.application', string='BNPL Application', ondelete='set null',
    )
    is_bnpl = fields.Boolean('BNPL Order', default=False)
