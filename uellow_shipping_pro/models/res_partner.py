# -*- coding: utf-8 -*-
"""
res.partner ↔ delivery.city
===========================
• `delivery_city_id` — pick the customer's city from the seeded list
  (640 map-matching cities across KW/SA/QA/AE/EG/OM/US). Selecting it
  syncs the plain `city` char field so everything else in Odoo keeps
  working (invoices, shipping labels, zone matching).
• Country defaults from the geo-IP of the person ENTERING the record
  (backoffice user creating a contact gets their own country pre-set).
"""
from odoo import api, fields, models
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    delivery_city_id = fields.Many2one(
        'delivery.city', string='City (list)',
        help='Pick from the delivery city list — keeps spelling identical '
             'to the maps and to the shipping zones.')

    @api.onchange('delivery_city_id')
    def _onchange_delivery_city_id(self):
        for p in self:
            if p.delivery_city_id:
                p.city = p.delivery_city_id.name_en
                if p.delivery_city_id.country_id:
                    p.country_id = p.delivery_city_id.country_id

    @api.onchange('country_id')
    def _onchange_country_filter_city(self):
        if self.country_id:
            return {'domain': {'delivery_city_id': [
                ('country_id', '=', self.country_id.id)]}}
        return {'domain': {'delivery_city_id': []}}

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Geo-IP country default for backoffice-created contacts.
        if 'country_id' in fields_list and not res.get('country_id'):
            try:
                geo = getattr(request, 'geoip', None)
                code = (geo.country_code if geo else '') or ''
                if code:
                    c = self.env['res.country'].sudo().search(
                        [('code', '=', code.upper())], limit=1)
                    if c:
                        res['country_id'] = c.id
            except Exception:
                pass
        return res
