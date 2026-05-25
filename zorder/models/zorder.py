from odoo import fields, models


class ZOrder(models.Model):
    _name = 'z.order'
    _description = 'ZOrder Quick Checkout'

    name            = fields.Char(string='Name', required=True)
    phone           = fields.Char(string='Phone', required=True)
    sale_order_id   = fields.Many2one('sale.order', string='Sale Order')
    partner_id      = fields.Many2one('res.partner', string='Customer')
    date            = fields.Datetime(default=fields.Datetime.now)
