from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_zorder = fields.Boolean(string='ZOrder Checkout', default=False)
