# -*- coding: utf-8 -*-
"""mobile.navbar — bottom nav bar configuration per (website, country).

Stored as JSON: a list of items, each with icon, label per-lang, target,
optional badge counter source, and visibility flags.
"""
import json

from odoo import api, fields, models


DEFAULT_ITEMS = [
    {'icon': '🏠', 'label': {'en': 'Home', 'ar': 'الرئيسية'},
     'target': {'type': 'page', 'value': 'home'}, 'badge': None, 'visible': True},
    {'icon': '🛍', 'label': {'en': 'Shop', 'ar': 'تسوّق'},
     'target': {'type': 'screen', 'value': 'shop'}, 'badge': None, 'visible': True},
    {'icon': '❤', 'label': {'en': 'Wishlist', 'ar': 'المفضّلة'},
     'target': {'type': 'screen', 'value': 'wishlist'}, 'badge': 'wishlist_count', 'visible': True},
    {'icon': '🛒', 'label': {'en': 'Cart', 'ar': 'السلة'},
     'target': {'type': 'screen', 'value': 'cart'}, 'badge': 'cart_count', 'visible': True},
    {'icon': '👤', 'label': {'en': 'Me', 'ar': 'حسابي'},
     'target': {'type': 'screen', 'value': 'account'}, 'badge': None, 'visible': True},
]


class MobileNavbar(models.Model):
    _name = 'mobile.navbar'
    _description = 'Mobile app bottom nav bar configuration'
    _order = 'website_id, id'

    name = fields.Char(required=True, default='Default')
    website_id = fields.Many2one('website', string='Website',
        help='Leave empty to apply to all sites that have no specific navbar')
    country_id = fields.Many2one('res.country', string='Country (optional)')
    items_json = fields.Text(default=lambda self: json.dumps(DEFAULT_ITEMS))
    active = fields.Boolean(default=True)
    active_color = fields.Char(default='#412402')
    inactive_color = fields.Char(default='#7A6850')
    show_labels = fields.Boolean(default=True)
    haptic = fields.Boolean(default=True)
    floating_action = fields.Char(
        help='Optional FAB target (page slug, "beena" for AI, etc.)')

    def to_admin_dict(self):
        self.ensure_one()
        try:
            items = json.loads(self.items_json or '[]')
        except Exception:
            items = []
        return {
            'id': self.id,
            'name': self.name,
            'website_id': self.website_id.id,
            'country_code': self.country_id and self.country_id.code or None,
            'items': items,
            'style': {
                'active_color': self.active_color,
                'inactive_color': self.inactive_color,
                'show_labels': self.show_labels,
                'haptic': self.haptic,
                'floating_action': self.floating_action,
            },
        }

    def to_public_dict(self, lang=None):
        """Flatten labels to the active lang."""
        d = self.to_admin_dict()
        for it in d['items']:
            lbl = it.get('label') or {}
            if isinstance(lbl, dict):
                it['label'] = lbl.get(lang or 'en') or lbl.get('en') or ''
        return d

    @api.model
    def get_for(self, website_id=None, country_code=None):
        """Pick the best-matching navbar for the given website+country."""
        Navbar = self.sudo()
        # Try specific match
        if website_id and country_code:
            country = self.env['res.country'].search([('code', '=', country_code)], limit=1)
            r = Navbar.search([('website_id', '=', website_id),
                               ('country_id', '=', country.id if country else False),
                               ('active', '=', True)], limit=1)
            if r:
                return r
        if website_id:
            r = Navbar.search([('website_id', '=', website_id),
                               ('country_id', '=', False),
                               ('active', '=', True)], limit=1)
            if r:
                return r
        return Navbar.search([('active', '=', True)], limit=1)
