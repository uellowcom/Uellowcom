# -*- coding: utf-8 -*-
"""
mobile.app.ad — in-app advertising (v2.1.27)
============================================
One model, three placements:

  • popup   — image/GIF/video dialog right after the app opens,
              with per-day / once-ever / every-time frequency capping.
  • splash  — full-screen flash ad on open that auto-dismisses after
              N seconds (skippable or not).
  • infeed  — ad tiles injected BETWEEN products in category grids,
              either every N products (fixed) or randomly, optionally
              limited to specific categories.

Every ad: bilingual title, image upload (PNG/JPG/GIF) or external image
URL or video URL, tap target (product / category / URL / none), date
range, per-website scoping (multi-website rule), live view/click stats.
"""
from odoo import api, fields, models


class MobileAppAd(models.Model):
    _name = 'mobile.app.ad'
    _description = 'Mobile App Ads'
    _order = 'sequence, id desc'

    name = fields.Char('Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    ad_type = fields.Selection([
        ('popup', '🪟 Popup on open'),
        ('splash', '⚡ Splash flash on open (auto-dismiss)'),
        ('infeed', '📦 In-feed (between products)'),
    ], required=True, default='popup', index=True, string='Type')

    # ── media ───────────────────────────────────────────────────────
    title_en = fields.Char('Title (EN)')
    title_ar = fields.Char('Title (AR)')
    image = fields.Image('Image (PNG/JPG/GIF)', max_width=1600,
                         max_height=1600)
    image_url = fields.Char('or External Image URL',
        help='CDN URL — used when no image is uploaded.')
    video_url = fields.Char('or Video URL (MP4/HLS)',
        help='Popup/Splash can play a muted auto-play video instead of '
             'an image.')

    # ── tap target ──────────────────────────────────────────────────
    link_type = fields.Selection([
        ('none', 'None'),
        ('product', 'Product'),
        ('category', 'Category'),
        ('url', 'URL'),
    ], default='none', string='On Tap')
    target_product_id = fields.Many2one('product.template', 'Target Product')
    target_category_id = fields.Many2one('product.public.category', 'Target Category')
    target_url = fields.Char('Target URL')

    # ── scheduling + scope ──────────────────────────────────────────
    date_from = fields.Datetime('Starts At')
    date_to = fields.Datetime('Ends At')
    website_ids = fields.Many2many(
        'website', 'mobile_app_ad_website_rel', 'ad_id', 'website_id',
        string='Websites', help='Empty = all websites')

    # ── popup options ───────────────────────────────────────────────
    popup_frequency = fields.Selection([
        ('always', 'Every app open'),
        ('day', 'Once per day'),
        ('once', 'Only once ever'),
    ], default='day', string='Frequency')
    popup_delay = fields.Integer('Show Delay (seconds)', default=1)

    # ── splash options ──────────────────────────────────────────────
    splash_seconds = fields.Integer('Display Duration (seconds)', default=4)
    splash_skippable = fields.Boolean('Skippable', default=True)

    # ── infeed options ──────────────────────────────────────────────
    infeed_mode = fields.Selection([
        ('every_n', 'Every N products'),
        ('random', 'Random'),
    ], default='every_n', string='Placement Mode')
    infeed_every_n = fields.Integer('Every N Products', default=8)
    infeed_category_ids = fields.Many2many(
        'product.public.category', 'mobile_app_ad_categ_rel',
        'ad_id', 'categ_id', string='Limit to Categories',
        help='Empty = all categories')

    # ── stats ───────────────────────────────────────────────────────
    view_count = fields.Integer('Views', readonly=True)
    click_count = fields.Integer('Clicks', readonly=True)
    ctr = fields.Float('CTR %', compute='_compute_ctr', store=False)

    @api.depends('view_count', 'click_count')
    def _compute_ctr(self):
        for a in self:
            a.ctr = round(a.click_count / a.view_count * 100.0, 2) \
                if a.view_count else 0.0

    @api.model
    def active_ads(self, ad_type, website_id=None, category_id=None):
        """Live ads for this placement, honouring schedule + website."""
        now = fields.Datetime.now()
        dom = [('ad_type', '=', ad_type), ('active', '=', True),
               '|', ('date_from', '=', False), ('date_from', '<=', now),
               '|', ('date_to', '=', False), ('date_to', '>=', now)]
        ads = self.sudo().search(dom, order='sequence, id desc')
        out = self.browse([])
        for a in ads:
            if website_id and a.website_ids and \
                    website_id not in a.website_ids.ids:
                continue
            if (ad_type == 'infeed' and category_id and a.infeed_category_ids
                    and category_id not in a.infeed_category_ids.ids):
                continue
            out |= a
        return out

    def register_event(self, event):
        self.ensure_one()
        if event == 'view':
            self.sudo().write({'view_count': self.view_count + 1})
        elif event == 'click':
            self.sudo().write({'click_count': self.click_count + 1})
