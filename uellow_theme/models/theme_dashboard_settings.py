"""Uellow Theme Settings — consolidated backend dashboard.

Replaces the scattered, frontend-only website settings with a single
backend menu where managers configure every theme-level toggle:
    - Header (preheader text, phone, search placeholder, trending tags)
    - Footer (about text, newsletter intro, credit line)
    - Mobile app (Play / App Store / AppGallery URLs)
    - Contact (WhatsApp, social links)
    - Storefront (delivery promise, warranty default)

Pattern: standalone TransientModel + a single `action_save` button. Each
field maps to either:
    A) ir.config_parameter (system-wide, key namespaced `uellow_theme.*`)
    B) website.<field> (per-website, falls back to current website)
"""
from odoo import models, fields, api, _


# ── (field_name on settings model, ICP key, default, type) ────────────
_ICP_KEYS = [
    # General — contact
    ('whatsapp_number',     'uellow_theme.whatsapp_number',       '+96597170933', str),
    ('preheader_text',      'uellow_theme.preheader_text',        '', str),
    ('preheader_phone',     'uellow_theme.preheader_phone',       '', str),
    ('search_placeholder',  'uellow_theme.search_placeholder',    'Search for products, brands and more...', str),
    ('trending_terms',      'uellow_theme.trending_terms',        '', str),
    # Mobile app URLs
    ('app_ios_url',         'uellow_theme.app_ios_url',           '', str),
    ('app_android_url',     'uellow_theme.app_android_url',       '', str),
    ('app_huawei_url',      'uellow_theme.app_huawei_url',        '', str),
    # Footer copy
    ('footer_about',        'uellow_theme.footer_about',          '', str),
    ('footer_credit',       'uellow_theme.footer_credit',         'Built with care in Kuwait', str),
    ('footer_newsletter_intro', 'uellow_theme.footer_newsletter_intro', 'Faster checkout, member-only deals, instant order updates.', str),
    # Free shipping bar
    ('free_shipping_text',  'uellow_theme.free_shipping_text',    'Free shipping on orders above 15 KWD', str),
    # Delivery / warranty defaults — also read by Beena
    ('delivery_time_text',  'uellow_ai.delivery_time_text',       'Same-day in Kuwait City before 2pm. 24–48h elsewhere.', str),
    ('default_warranty',    'uellow_theme.default_warranty',      'Uellow 1-year warranty — 24h delivery', str),
    # Social URLs (one per line)
    ('social_urls',         'uellow_theme.social_urls',           '', str),
    # Feature toggles
    ('enable_beena',        'uellow_theme.enable_beena',          True, bool),
    ('enable_fast_buy',     'uellow_theme.enable_fast_buy',       True, bool),
    ('enable_compare',      'uellow_theme.enable_compare',        True, bool),
    ('enable_wishlist',     'uellow_theme.enable_wishlist',       True, bool),
    ('enable_bulk_pricing', 'uellow_theme.enable_bulk_pricing',   True, bool),
    ('enable_view_counter', 'uellow_theme.enable_view_counter',   True, bool),
    ('enable_stats_strip',  'uellow_theme.enable_stats_strip',    True, bool),
    # Brand colours (read by SCSS via website.assets _variables — bonus
    # field; until SCSS vars are wired, this is a future-proof slot)
    ('brand_yellow',        'uellow_theme.brand_yellow',          '#F5C320', str),
    ('brand_dark',          'uellow_theme.brand_dark',            '#412402', str),
]


def _coerce(val, typ, default):
    if val in (None, ''):
        return default
    try:
        if typ is bool:
            return str(val).strip().lower() in ('1', 'true', 'yes', 'on')
        if typ is int:
            return int(val)
        return str(val)
    except (TypeError, ValueError):
        return default


class UellowThemeSettings(models.TransientModel):
    _name = 'uellow.theme.settings'
    _description = 'Uellow Theme Settings'

    # ── General / Contact ──
    whatsapp_number    = fields.Char('WhatsApp Number',
        help='Full international format, e.g. +96597170933')
    preheader_text     = fields.Char('Preheader Banner Text',
        help='Top thin bar — promo strip ("Free shipping over 15 KWD" etc.)')
    preheader_phone    = fields.Char('Preheader Phone')

    # ── Search ──
    search_placeholder = fields.Char('Search Bar Placeholder')
    trending_terms     = fields.Char('Trending Search Terms (comma-separated)')

    # ── Mobile App ──
    app_ios_url        = fields.Char('App Store URL (iOS)')
    app_android_url    = fields.Char('Google Play URL (Android)')
    app_huawei_url     = fields.Char('AppGallery URL (Huawei)')

    # ── Footer copy ──
    footer_about       = fields.Text('Footer About Paragraph')
    footer_credit      = fields.Char('Footer Credit Line')
    footer_newsletter_intro = fields.Text('Newsletter Intro Paragraph')
    free_shipping_text = fields.Char('Free Shipping Bar Text')

    # ── Storefront ──
    delivery_time_text = fields.Text('Delivery Time Text',
        help='Shown in the Shipping tab on every product page. Also read by Beena AI.')
    default_warranty   = fields.Char('Default Product Warranty')

    # ── Social ──
    social_urls        = fields.Text('Social Profile URLs',
        help='One URL per line — Instagram, X, Facebook, TikTok, YouTube…')

    # ── Feature toggles ──
    enable_beena        = fields.Boolean('Enable Beena AI Chat', default=True)
    enable_fast_buy     = fields.Boolean('Enable Fast Buy', default=True)
    enable_compare      = fields.Boolean('Enable Product Compare', default=True)
    enable_wishlist     = fields.Boolean('Enable Wishlist', default=True)
    enable_bulk_pricing = fields.Boolean('Show Bulk Pricing Block', default=True)
    enable_view_counter = fields.Boolean('Show View Counter on Products', default=True)
    enable_stats_strip  = fields.Boolean('Show Stats Strip Below Gallery', default=True)

    # ── Brand colours ──
    brand_yellow = fields.Char('Brand Yellow Colour', default='#F5C320')
    brand_dark   = fields.Char('Brand Dark Colour', default='#412402')

    # ──────────────────────────────────────────────────────────────────
    # default_get & action_save driven by _ICP_KEYS so adding a setting
    # needs ONE line not three.
    # ──────────────────────────────────────────────────────────────────
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        icp = self.env['ir.config_parameter'].sudo()
        for field_name, key, default, typ in _ICP_KEYS:
            res[field_name] = _coerce(icp.get_param(key), typ, default)
        return res

    def action_save(self):
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        for field_name, key, _default, typ in _ICP_KEYS:
            val = getattr(self, field_name, None)
            if typ is bool:
                icp.set_param(key, '1' if val else '0')
            elif val is False or val is None:
                icp.set_param(key, '')
            else:
                icp.set_param(key, str(val))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Saved'),
                'message': _('Uellow Theme settings updated.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_reset_assets(self):
        """Clear compiled assets cache so SCSS / JS rebuild on next page hit."""
        self.ensure_one()
        self.env.cr.execute("DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%'")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Assets cleared'),
                'message': _('Hard-refresh any open page to load new assets.'),
                'type': 'info',
            },
        }
