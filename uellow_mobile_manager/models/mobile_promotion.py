# -*- coding: utf-8 -*-
"""
mobile.app.promotion — marketplace promotion campaigns (v2.1.30)
================================================================
Campaigns like Mother's Day, Eid, Black Friday… managed from the Mobile
App Manager. Each promotion carries a coin badge (emoji + colors) that
the app renders INLINE before the product name on cards and beside the
gallery banner on the product page, plus a builder block source.

Product participation comes from two doors:
  • Admin adds products directly (auto-approved lines).
  • VENDORS browse open promotions in their portal, pick their products
    + a discount % each, and submit a join request — admin approves or
    rejects line by line.

Optional pricing automation (apply_discounts): when the promotion goes
RUNNING the approved lines get their discount applied (old price saved
as compare price), and everything is restored when it ends. OFF by
default — badges only.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PRESETS = [
    ('mothers_day', "💐 Mother's Day"),
    ('eid', '🌙 Eid'),
    ('ramadan', '🏮 Ramadan'),
    ('national_day', '🇰🇼 National Day'),
    ('black_friday', '🖤 Black Friday'),
    ('white_friday', '🤍 White Friday'),
    ('back_to_school', '🎒 Back to School'),
    ('summer', '☀️ Summer Sale'),
    ('flash', '⚡ Flash Deals'),
    ('new_year', '🎆 New Year'),
    ('custom', '🎯 Custom'),
]

PRESET_DEFAULTS = {
    'mothers_day': ('💐', "Mother's Day", 'عيد الأم', '#FCE4EC', '#C2185B'),
    'eid': ('🌙', 'Eid Offers', 'عروض العيد', '#E8F5E9', '#1B5E20'),
    'ramadan': ('🏮', 'Ramadan Deals', 'عروض رمضان', '#FFF3E0', '#B26A00'),
    'national_day': ('🇰🇼', 'National Day', 'العيد الوطني', '#E3F2FD', '#0D47A1'),
    'black_friday': ('🖤', 'Black Friday', 'الجمعة السوداء', '#212121', '#FFFFFF'),
    'white_friday': ('🤍', 'White Friday', 'الجمعة البيضاء', '#F5F5F5', '#212121'),
    'back_to_school': ('🎒', 'Back to School', 'العودة للمدارس', '#E8EAF6', '#283593'),
    'summer': ('☀️', 'Summer Sale', 'تخفيضات الصيف', '#FFFDE7', '#F57F17'),
    'flash': ('⚡', 'Flash Deals', 'عروض فلاش', '#FFF8E1', '#FF6F00'),
    'new_year': ('🎆', 'New Year', 'رأس السنة', '#EDE7F6', '#4527A0'),
    'custom': ('🎯', 'Special Offer', 'عرض خاص', '#FFF8E1', '#8B6508'),
}


class MobileAppPromotion(models.Model):
    _name = 'mobile.app.promotion'
    _description = 'Mobile App Promotion Campaign'
    _order = 'sequence, date_from desc'

    name = fields.Char('Internal Name', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    preset = fields.Selection(PRESETS, default='custom', required=True,
        help='Picking a preset prefills the badge (emoji, labels, colors).')

    # ── badge (the coin) ────────────────────────────────────────────
    emoji = fields.Char('Badge Emoji', default='🎯', size=8)
    label_en = fields.Char('Badge Label (EN)', default='Special Offer')
    label_ar = fields.Char('Badge Label (AR)', default='عرض خاص')
    bg_color = fields.Char('Badge Background', default='#FFF8E1',
                           help='Hex color, e.g. #FFF8E1')
    fg_color = fields.Char('Badge Text Color', default='#8B6508')
    banner_image = fields.Image('Product-page Banner (deprecated)',
        max_width=1600,
        help='DEPRECATED — replaced by the flash-sale-style banner below.')

    # ── product-page banner (flash-sale style, v2.1.35) ─────────────
    banner_enabled = fields.Boolean('Show Product-page Banner', default=True,
        help='Render a flash-sale-style strip (icon + gradient + countdown) '
             'under the gallery on participating product pages.')
    banner_title_en = fields.Char('Banner Title (EN)')
    banner_title_ar = fields.Char('Banner Title (AR)')
    banner_subtitle_en = fields.Char('Banner Subtitle (EN)')
    banner_subtitle_ar = fields.Char('Banner Subtitle (AR)')
    banner_color_1 = fields.Char('Banner Color 1', default='#F5C320',
        help='Hex. With Color 2 set → gradient; alone → solid color.')
    banner_color_2 = fields.Char('Banner Color 2 (gradient end)',
        default='#EA580C', help='Hex. Leave empty for a single solid color.')
    banner_pattern = fields.Boolean('Pattern Overlay', default=True,
        help='Subtle white pattern over the banner color.')
    banner_pattern_style = fields.Selection([
        ('stripes', 'Diagonal stripes'),
        ('stripes_bold', 'Bold stripes'),
        ('crosshatch', 'Crosshatch'),
        ('mesh', 'Fine mesh'),
        ('grid', 'Grid'),
        ('dots', 'Micro dots'),
        ('polka', 'Polka dots'),
        ('bubbles', 'Bubbles'),
        ('circles', 'Circle outlines'),
        ('rings', 'Corner rings'),
        ('scales', 'Fish scales'),
        ('waves', 'Waves'),
        ('zigzag', 'Zigzag'),
        ('chevrons', 'Chevrons'),
        ('diamonds', 'Diamonds'),
        ('triangles', 'Triangles'),
        ('hexagons', 'Hexagons'),
        ('plus', 'Plus signs'),
        ('sparkles', 'Sparkles'),
        ('stars', 'Stars'),
        ('confetti', 'Confetti'),
        ('moons', 'Crescents'),
    ], string='Pattern Style', default='stripes')
    banner_icon = fields.Image('Banner Icon', max_width=256, max_height=256,
        help='Round icon shown at the start of the product-page banner '
             '(replaces the discount % circle when set).')
    banner_icon_bg = fields.Char('Icon Circle Color', default='#FFFFFF',
        help='Background color of the round icon holder on the banner.')

    # ── schedule + scope ────────────────────────────────────────────
    date_from = fields.Datetime('Starts At', required=True)
    date_to = fields.Datetime('Ends At', required=True)
    website_ids = fields.Many2many(
        'website', 'mobile_promo_website_rel', 'promo_id', 'website_id',
        string='Websites', help='Empty = all websites')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Vendors'),
        ('running', 'Running'),
        ('ended', 'Ended'),
    ], default='draft', required=True, index=True, tracking=False)

    # ── behaviour ───────────────────────────────────────────────────
    vendor_joinable = fields.Boolean('Vendors Can Join', default=True,
        help='Show this promotion in the vendor portal so vendors can '
             'request to join with their products.')
    apply_discounts = fields.Boolean('Auto-apply Discounts', default=False,
        help='DANGER ZONE: when the promotion starts, approved lines get '
             'their discount applied to the live price (old price kept as '
             'the strikethrough compare price) and restored when it ends. '
             'Leave OFF for badge-only campaigns.')
    min_discount_pct = fields.Float('Min Discount % for Vendors', default=5.0)
    max_discount_pct = fields.Float('Max Discount % for Vendors', default=90.0)

    line_ids = fields.One2many('mobile.promotion.line', 'promotion_id')
    approved_count = fields.Integer(compute='_compute_counts')
    pending_count = fields.Integer(compute='_compute_counts')

    @api.depends('line_ids.state')
    def _compute_counts(self):
        for p in self:
            p.approved_count = len(p.line_ids.filtered(
                lambda l: l.state == 'approved'))
            p.pending_count = len(p.line_ids.filtered(
                lambda l: l.state == 'pending'))

    @api.onchange('preset')
    def _onchange_preset(self):
        d = PRESET_DEFAULTS.get(self.preset)
        if d:
            self.emoji, self.label_en, self.label_ar, \
                self.bg_color, self.fg_color = d

    # ── lifecycle ───────────────────────────────────────────────────
    def action_open(self):
        self.write({'state': 'open'})

    def action_start(self):
        for p in self:
            p.state = 'running'
            if p.apply_discounts:
                p._apply_prices()

    def action_end(self):
        for p in self:
            if p.apply_discounts:
                p._restore_prices()
            p.state = 'ended'

    def action_reset_draft(self):
        """v2.1.37 — bring a stopped/ended (or open/running) campaign back
        to DRAFT so it can be re-dated and reused. Prices are restored
        first if the campaign had auto-discounts applied; vendor lines and
        their approvals are kept."""
        for p in self:
            if p.apply_discounts and p.state == 'running':
                p._restore_prices()
            p.state = 'draft'

    def _apply_prices(self):
        for l in self.line_ids.filtered(
                lambda l: l.state == 'approved' and l.discount_pct > 0):
            try:
                tmpl = l.product_tmpl_id
                l.old_list_price = tmpl.list_price
                l.old_compare_price = tmpl.compare_list_price or 0.0
                tmpl.write({
                    'compare_list_price': tmpl.list_price,
                    'list_price': round(
                        tmpl.list_price * (1 - l.discount_pct / 100.0), 3),
                })
                l.price_applied = True
            except Exception:
                _logger.exception('promo price apply failed line %s', l.id)

    def _restore_prices(self):
        for l in self.line_ids.filtered('price_applied'):
            try:
                l.product_tmpl_id.write({
                    'list_price': l.old_list_price,
                    'compare_list_price': l.old_compare_price,
                })
                l.price_applied = False
            except Exception:
                _logger.exception('promo price restore failed line %s', l.id)

    @api.model
    def cron_lifecycle(self):
        """Auto start/end by dates (runs hourly)."""
        now = fields.Datetime.now()
        for p in self.sudo().search([('state', 'in', ('open', 'running'))]):
            if p.state != 'running' and p.date_from <= now <= p.date_to:
                p.action_start()
            elif p.state == 'running' and now > p.date_to:
                p.action_end()

    # ── lookups ─────────────────────────────────────────────────────
    @api.model
    def badge_for(self, product_tmpl_id, website_id=None):
        """The active promotion badge for a product (or None)."""
        now = fields.Datetime.now()
        lines = self.env['mobile.promotion.line'].sudo().search([
            ('product_tmpl_id', '=', product_tmpl_id),
            ('state', '=', 'approved'),
            ('promotion_id.state', '=', 'running'),
            ('promotion_id.active', '=', True),
            ('promotion_id.date_from', '<=', now),
            ('promotion_id.date_to', '>=', now),
        ], limit=3)
        for l in lines:
            p = l.promotion_id
            if website_id and p.website_ids and \
                    website_id not in p.website_ids.ids:
                continue
            return {
                'id': p.id,
                'emoji': p.emoji or '🎯',
                'label': {'en': p.label_en or '', 'ar': p.label_ar or p.label_en or ''},
                'bg': p.bg_color or '#FFF8E1',
                'fg': p.fg_color or '#8B6508',
                'discount_pct': l.discount_pct,
                'ends_at': p.date_to.isoformat() if p.date_to else None,
                'has_banner': bool(p.banner_image),
                # v2.1.35 — flash-sale-style product-page banner config.
                'banner': {
                    'title': {
                        'en': p.banner_title_en or p.label_en or '',
                        'ar': p.banner_title_ar or p.label_ar
                              or p.banner_title_en or '',
                    },
                    'subtitle': {
                        'en': p.banner_subtitle_en or '',
                        'ar': p.banner_subtitle_ar
                              or p.banner_subtitle_en or '',
                    },
                    'colors': [c for c in (p.banner_color_1,
                                           p.banner_color_2) if c],
                    'pattern': bool(p.banner_pattern),
                    'pattern_style': p.banner_pattern_style or 'stripes',
                    'emoji': p.emoji or '🎯',
                    # public icon route (guests lack model read ACL)
                    'icon_url': ('/api/mobile/v2/promotions/%s/icon?u=%s'
                                 % (p.id, int(p.write_date.timestamp())))
                                if p.banner_icon else '',
                    'icon_bg': p.banner_icon_bg or '#FFFFFF',
                } if p.banner_enabled else None,
            }
        return None


class MobilePromotionLine(models.Model):
    _name = 'mobile.promotion.line'
    _description = 'Promotion Product Line'
    _order = 'promotion_id, vendor_id, id'

    promotion_id = fields.Many2one('mobile.app.promotion', required=True,
                                   ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', required=True,
                                      ondelete='cascade', index=True,
                                      string='Product')
    vendor_id = fields.Many2one('uellow.vendor', index=True,
        help='Empty = added directly by the marketplace admin.')
    discount_pct = fields.Float('Discount %', default=10.0)
    state = fields.Selection([
        ('pending', '⏳ Pending'),
        ('approved', '✅ Approved'),
        ('rejected', '❌ Rejected'),
    ], default='pending', required=True, index=True)
    note = fields.Char('Vendor Note')
    reject_reason = fields.Char('Rejection Reason')
    # rollback bookkeeping for apply_discounts
    price_applied = fields.Boolean(readonly=True)
    old_list_price = fields.Float(readonly=True)
    old_compare_price = fields.Float(readonly=True)

    _sql_constraints = [
        ('uniq_promo_product', 'unique(promotion_id, product_tmpl_id)',
         'This product is already in the promotion.'),
    ]

    def action_approve(self):
        self.write({'state': 'approved'})
        for l in self:
            if (l.promotion_id.state == 'running'
                    and l.promotion_id.apply_discounts
                    and not l.price_applied):
                l.promotion_id._apply_prices()

    def action_reject(self):
        self.write({'state': 'rejected'})
