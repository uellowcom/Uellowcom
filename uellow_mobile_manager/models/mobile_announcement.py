# -*- coding: utf-8 -*-
"""Targeted announcement strips (v2.1.57).

Slim bars the app shows on chosen screens to a chosen AUDIENCE —
"new-user bonus", "free shipping weekend", "rate us", etc. Fully
admin-controlled: content (bilingual), look (colors + emoji), placement
(screens), audience, schedule, website scope, CTA link, dismissibility.
"""
from datetime import timedelta

from odoo import api, fields, models


class MobileAnnouncement(models.Model):
    _name = 'mobile.announcement'
    _description = 'Mobile app announcement strip'
    _order = 'sequence, id desc'

    name = fields.Char('Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # ── content ──
    message_en = fields.Char('Message (EN)', required=True)
    message_ar = fields.Char('Message (AR)')
    emoji = fields.Char('Emoji', default='🎁', size=8)
    cta_label_en = fields.Char('Button Label (EN)', default='Get')
    cta_label_ar = fields.Char('Button Label (AR)', default='احصل عليها')

    # ── look ──
    bg_color = fields.Char('Bar Color', default='#412402',
        help='Hex like #412402. The strip background.')
    text_color = fields.Char('Text Color', default='#FFFFFF')
    button_color = fields.Char('Button Color', default='#F5C320')
    button_text_color = fields.Char('Button Text Color', default='#412402')

    # ── placement (screens) ──
    show_on_home = fields.Boolean('Home', default=True)
    show_on_cart = fields.Boolean('Cart')
    show_on_shop = fields.Boolean('Shop')
    show_on_account = fields.Boolean('Account')
    show_on_product = fields.Boolean('Product page')

    # ── audience ──
    audience = fields.Selection([
        ('all', '👥 Everyone'),
        ('guests', '👤 Guests (not signed in)'),
        ('registered', '✅ Signed-in customers'),
        ('new_customers', '✨ New customers (no orders yet)'),
        ('has_orders', '🛍 Customers with orders'),
        ('inactive_30d', '😴 Inactive 30+ days (no recent order)'),
    ], default='all', required=True)

    # ── CTA link ──
    link_type = fields.Selection([
        ('none', 'No action'),
        ('screen', 'App screen'),
        ('product', 'Product'),
        ('category', 'Category'),
        ('url', 'URL'),
    ], default='screen', required=True, string='Tap action')
    link_screen = fields.Selection([
        ('coupons', 'Coupons'), ('shop', 'Shop'), ('flash', 'Flash sale'),
        ('loyalty', 'Loyalty'), ('wallet', 'Wallet'),
        ('notifications', 'Notifications'), ('account', 'Account'),
    ], default='coupons')
    link_product_id = fields.Many2one('product.template', string='Product')
    link_category_id = fields.Many2one('product.public.category',
                                       string='Category')
    link_url = fields.Char('URL')

    # ── behaviour + scope ──
    dismissible = fields.Boolean('Customer can dismiss (×)', default=True)
    date_from = fields.Datetime('Starts At')
    date_to = fields.Datetime('Ends At')
    website_ids = fields.Many2many(
        'website', 'mobile_announcement_website_rel',
        'announcement_id', 'website_id', string='Websites',
        help='Empty = all websites')

    def _matches_audience(self, partner):
        """Does this strip target the given partner (None = guest)?"""
        self.ensure_one()
        aud = self.audience
        if aud == 'all':
            return True
        if aud == 'guests':
            return not partner
        if not partner:
            return False        # the rest need a signed-in customer
        if aud == 'registered':
            return True
        Sale = self.env['sale.order'].sudo()
        commercial = partner.commercial_partner_id or partner
        order_dom = [('partner_id', 'child_of', commercial.id),
                     ('state', 'in', ('sale', 'done'))]
        if aud == 'new_customers':
            return Sale.search_count(order_dom) == 0
        if aud == 'has_orders':
            return Sale.search_count(order_dom) > 0
        if aud == 'inactive_30d':
            cutoff = fields.Datetime.now() - timedelta(days=30)
            recent = Sale.search_count(
                order_dom + [('date_order', '>=', cutoff)])
            had_any = Sale.search_count(order_dom) > 0
            return had_any and recent == 0
        return False

    @api.model
    def for_screen(self, screen, partner=None, website_id=None):
        """Active strips for a screen + audience, serialized for the app."""
        field = {
            'home': 'show_on_home', 'cart': 'show_on_cart',
            'shop': 'show_on_shop', 'account': 'show_on_account',
            'product': 'show_on_product',
        }.get(screen)
        if not field:
            return []
        now = fields.Datetime.now()
        dom = [(field, '=', True), ('active', '=', True),
               '|', ('date_from', '=', False), ('date_from', '<=', now),
               '|', ('date_to', '=', False), ('date_to', '>=', now)]
        out = []
        for a in self.sudo().search(dom):
            if website_id and a.website_ids and \
                    website_id not in a.website_ids.ids:
                continue
            if not a._matches_audience(partner):
                continue
            link = {'type': 'none', 'value': ''}
            if a.link_type == 'screen' and a.link_screen:
                link = {'type': 'screen', 'value': a.link_screen}
            elif a.link_type == 'product' and a.link_product_id:
                link = {'type': 'product', 'value': a.link_product_id.id}
            elif a.link_type == 'category' and a.link_category_id:
                link = {'type': 'category', 'value': a.link_category_id.id}
            elif a.link_type == 'url' and a.link_url:
                link = {'type': 'url', 'value': a.link_url}
            out.append({
                'id': a.id,
                'message': {'en': a.message_en or '',
                            'ar': a.message_ar or a.message_en or ''},
                'emoji': a.emoji or '🎁',
                'cta': {'en': a.cta_label_en or '',
                        'ar': a.cta_label_ar or a.cta_label_en or ''},
                'bg': a.bg_color or '#412402',
                'fg': a.text_color or '#FFFFFF',
                'btn_bg': a.button_color or '#F5C320',
                'btn_fg': a.button_text_color or '#412402',
                'dismissible': a.dismissible,
                'link': link,
            })
        return out
