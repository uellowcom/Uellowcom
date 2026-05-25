# -*- coding: utf-8 -*-
from odoo import fields, models


class UcOrder(models.Model):
    _name        = 'uc.order'
    _description = 'Uellow Checkout Order'
    _order       = 'date desc'

    name           = fields.Char(string='Customer Name', required=True)
    phone          = fields.Char(string='Phone',         required=True)
    email          = fields.Char(string='Email')
    sale_order_id  = fields.Many2one('sale.order',  string='Sale Order')
    partner_id     = fields.Many2one('res.partner', string='Customer')
    payment_method = fields.Char(string='Payment Method')
    governorate    = fields.Char(string='Governorate / State')
    city           = fields.Char(string='City')
    street         = fields.Char(string='Street Address')
    full_address   = fields.Text(string='Full Address')
    order_notes    = fields.Text(string='Order Notes')
    latitude       = fields.Float(string='Latitude',  digits=(10, 8))
    longitude      = fields.Float(string='Longitude', digits=(11, 8))
    date           = fields.Datetime(string='Date', default=fields.Datetime.now)
    map_url        = fields.Char(string='Map Link', compute='_compute_map_url', store=False)

    def _compute_map_url(self):
        for r in self:
            r.map_url = (
                'https://www.google.com/maps?q=%.8f,%.8f' % (r.latitude, r.longitude)
                if r.latitude and r.longitude else False
            )
