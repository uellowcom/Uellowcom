# -*- coding: utf-8 -*-
"""v2.2.00 — Unified Uellow address on res.partner.

The app's detailed address form (governorate → area → block/street/
building/floor/apartment + GPS pin + label) is now mirrored 1:1 in the
back-office: structured fields, the customer's coordinates, and an
EMBEDDED MAP right on the partner form, so what the customer entered is
exactly what operations sees.
"""
from odoo import api, fields, models


class ResPartnerUellowAddress(models.Model):
    _inherit = 'res.partner'

    uellow_governorate_id = fields.Many2one(
        'uellow.governorate', string='Governorate / المحافظة',
        help='Unified governorate — same list the app and website use.')
    uellow_city_id = fields.Many2one(
        'uellow.city', string='Area / المنطقة',
        domain="[('governorate_id', '=?', uellow_governorate_id)]",
        help='Unified area/city — same list the app and website use.')
    uellow_block = fields.Char('Block / القطعة')
    uellow_building = fields.Char('Building / المبنى')
    uellow_floor = fields.Char('Floor / الدور')
    uellow_apartment = fields.Char('Apartment / الشقة')
    uellow_address_label = fields.Char('Label / التسمية',
                                       help='Home / Work / Mum\'s …')
    uellow_map_html = fields.Html(
        'Map', compute='_compute_uellow_map_html', sanitize=False)

    @api.depends('partner_latitude', 'partner_longitude')
    def _compute_uellow_map_html(self):
        for p in self:
            lat, lng = p.partner_latitude, p.partner_longitude
            if not lat and not lng:
                p.uellow_map_html = (
                    '<div style="padding:18px;background:#f6f6f6;'
                    'border-radius:10px;color:#888;text-align:center">'
                    '📍 No GPS pin saved for this address yet — the customer '
                    'hasn\'t dropped a map pin in the app.</div>')
                continue
            d = 0.004
            bbox = '%.6f,%.6f,%.6f,%.6f' % (lng - d, lat - d, lng + d, lat + d)
            p.uellow_map_html = (
                '<iframe width="100%%" height="330" frameborder="0" '
                'style="border-radius:12px;border:1px solid #e5e5e5" '
                'src="https://www.openstreetmap.org/export/embed.html'
                '?bbox=%s&amp;layer=mapnik&amp;marker=%.6f,%.6f"></iframe>'
                '<div style="margin-top:6px;font-size:12px;color:#666">'
                'Lat: <b>%.6f</b> &nbsp;·&nbsp; Lng: <b>%.6f</b></div>'
                % (bbox, lat, lng, lat, lng))

    def action_open_in_gmaps(self):
        self.ensure_one()
        if not (self.partner_latitude or self.partner_longitude):
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': 'https://maps.google.com/?q=%.6f,%.6f' % (
                self.partner_latitude, self.partner_longitude),
            'target': 'new',
        }
