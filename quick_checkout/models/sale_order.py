from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_quick_checkout = fields.Boolean(string='Is Quick Checkout', default=False)
    quick_checkout_id = fields.Many2one('quick.checkout', string='Quick Checkout', readonly=True)
