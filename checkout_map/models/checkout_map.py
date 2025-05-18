from odoo import api, fields, models

class CheckoutMap(models.Model):
    _name = 'checkout.map'
    _description = 'Checkout Map Location'

    name = fields.Char(string='Location Name')
    latitude = fields.Float(string='Latitude')
    longitude = fields.Float(string='Longitude')
    address = fields.Text(string='Address')
    partner_id = fields.Many2one('res.partner', string='Partner')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    
    def name_get(self):
        result = []
        for record in self:
            name = record.name or f"Location ({record.latitude}, {record.longitude})"
            result.append((record.id, name))
        return result
