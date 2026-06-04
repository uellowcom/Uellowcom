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
    _description = 'إعلانات التطبيق'
    _order = 'sequence, id desc'

    name = fields.Char('الاسم الداخلي', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    ad_type = fields.Selection([
        ('popup', '🪟 Popup عند الفتح'),
        ('splash', '⚡ فلاش عند الفتح (يختفي تلقائياً)'),
        ('infeed', '📦 وسط المنتجات'),
    ], required=True, default='popup', index=True, string='النوع')

    # ── media ───────────────────────────────────────────────────────
    title_en = fields.Char('العنوان (EN)')
    title_ar = fields.Char('العنوان (AR)')
    image = fields.Image('الصورة (PNG/JPG/GIF)', max_width=1600,
                         max_height=1600)
    image_url = fields.Char('أو رابط صورة خارجي',
        help='CDN URL — used when no image is uploaded.')
    video_url = fields.Char('أو رابط فيديو (MP4/HLS)',
        help='Popup/Splash can play a muted auto-play video instead of '
             'an image.')

    # ── tap target ──────────────────────────────────────────────────
    link_type = fields.Selection([
        ('none', 'بدون'),
        ('product', 'منتج'),
        ('category', 'قسم'),
        ('url', 'رابط'),
    ], default='none', string='عند الضغط')
    target_product_id = fields.Many2one('product.template', 'المنتج')
    target_category_id = fields.Many2one('product.public.category', 'القسم')
    target_url = fields.Char('الرابط')

    # ── scheduling + scope ──────────────────────────────────────────
    date_from = fields.Datetime('يبدأ في')
    date_to = fields.Datetime('ينتهي في')
    website_ids = fields.Many2many(
        'website', 'mobile_app_ad_website_rel', 'ad_id', 'website_id',
        string='الويبسايتات', help='فارغ = كل الويبسايتات')

    # ── popup options ───────────────────────────────────────────────
    popup_frequency = fields.Selection([
        ('always', 'كل مرة يفتح التطبيق'),
        ('day', 'مرة واحدة يومياً'),
        ('once', 'مرة واحدة فقط'),
    ], default='day', string='تكرار الظهور')
    popup_delay = fields.Integer('تأخير الظهور (ثواني)', default=1)

    # ── splash options ──────────────────────────────────────────────
    splash_seconds = fields.Integer('مدة العرض (ثواني)', default=4)
    splash_skippable = fields.Boolean('قابل للتخطي', default=True)

    # ── infeed options ──────────────────────────────────────────────
    infeed_mode = fields.Selection([
        ('every_n', 'كل N منتج'),
        ('random', 'عشوائي'),
    ], default='every_n', string='طريقة التوزيع')
    infeed_every_n = fields.Integer('كل كم منتج', default=8)
    infeed_category_ids = fields.Many2many(
        'product.public.category', 'mobile_app_ad_categ_rel',
        'ad_id', 'categ_id', string='في الأقسام',
        help='فارغ = كل الأقسام')

    # ── stats ───────────────────────────────────────────────────────
    view_count = fields.Integer('المشاهدات', readonly=True)
    click_count = fields.Integer('النقرات', readonly=True)
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
