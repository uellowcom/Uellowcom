from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_fast_buy = fields.Boolean(string='Is Quick Checkout', default=False)
    fast_buy_id = fields.Many2one('fast.buy', string='Quick Checkout', readonly=True)
