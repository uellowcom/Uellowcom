from odoo import fields, models


class FastBuy(models.Model):
    _name = 'fast.buy'
    _description = 'Quick Checkout'

    name = fields.Char(string='Name', required=True)
    phone = fields.Char(string='Phone', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    partner_id = fields.Many2one('res.partner', string='Customer')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
