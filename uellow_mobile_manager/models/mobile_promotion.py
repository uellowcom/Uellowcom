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

    # ════════════════════════════════════════════════════════════════
    # v2.2.48 — RULES ENGINE: targeting + margin guard + channel + caps
    # + rewards. Additive; the legacy badge/vendor-line flow keeps working.
    # ════════════════════════════════════════════════════════════════

    # ── الاستهداف بالقواعد (Targeting) ───────────────────────────────
    target_mode = fields.Selection([
        ('manual', '🖐️ Manual product lines (legacy)'),
        ('rules',  '🎯 Rule-based scopes'),
    ], default='manual', required=True,
        help='Rules mode auto-selects products from the scopes below and '
             'auto-builds discounted lines (margin-guarded).')
    scope_ids = fields.One2many('mobile.promo.scope', 'promotion_id',
                                string='Targeting Scopes')
    global_discount_pct = fields.Float('Discount % (rules)', default=15.0,
        help='Requested discount for rule-targeted products. The margin '
             'guard may reduce it per product.')
    targeted_count = fields.Integer('Targeted Products',
                                    compute='_compute_targeted', store=False)
    excluded_count = fields.Integer('Excluded (total)',
                                    compute='_compute_targeted', store=False)
    below_min_count = fields.Integer('Hidden (weak discount)',
                                     compute='_compute_targeted', store=False)

    # ── حد أدنى للخصم المعروض ─────────────────────────────────────────
    # المنتجات التي لا يبقى لها بعد حارس الربح سوى خصم ضعيف (مثلاً < 5%)
    # تُستبعَد من العرض — فالعرض الترويجي يجب أن يبدو "عرضاً" حقيقياً لا
    # خصماً رمزياً يفسد مصداقية الحملة.
    min_show_discount_pct = fields.Float('Min discount % to show', default=0.0,
        help='Hide any product whose EFFECTIVE discount (after the margin '
             'guard) would fall below this %. 0 = show every discounted '
             'product, however small. e.g. 5 = a "Sale" never shows a 0.3% '
             'product.')

    # ── حارس الربح (Margin Guard) ────────────────────────────────────
    margin_guard = fields.Boolean('Protect Profit Margin', default=True)
    margin_mode = fields.Selection([
        ('cap',    'Cap the discount to keep the floor'),
        ('derive', 'Derive max discount from the floor'),
    ], default='cap', string='Margin Mode')
    min_margin_pct = fields.Float('Min Profit Margin %', default=10.0,
        help='No product is discounted below this profit floor. Products '
             'whose cost cannot meet it are excluded automatically.')
    # احتساب تكلفة التوصيل ضمن الربح: عند تفعيله يُعامَل مبلغ التوصيل كأنه
    # جزء من التكلفة، فيبقى الربح المتبقّي كافياً لتغطية التوصيل المجاني.
    margin_reserve_ship = fields.Boolean('Reserve delivery cost', default=False,
        help='When on, the delivery amount is treated as extra cost so the '
             'remaining profit still covers free delivery before the floor is '
             'measured.')
    margin_ship_cost = fields.Float('Delivery cost to reserve', default=1.250,
        help='Delivery amount (e.g. 1.250) added to the product cost when '
             'reserving for free delivery.')

    # ── القناة (Channel) ─────────────────────────────────────────────
    channel = fields.Selection([
        ('mobile',  '📱 Mobile only'),
        ('both',    '📱+🌐 Mobile + Website'),
        ('website', '🌐 Website only'),
        ('pos',     '📱+🌐+🏬 incl. POS'),
    ], default='both', required=True)

    # ── السقوف (Caps) ────────────────────────────────────────────────
    priority = fields.Integer('Priority', default=10,
        help='Higher wins when several promotions match the same product.')
    stackable = fields.Boolean('Stackable with others', default=True)
    exclusive = fields.Boolean('Exclusive (suppresses others)', default=False)
    usage_limit = fields.Integer('Total usage limit', default=0,
        help='0 = unlimited.')
    per_customer_limit = fields.Integer('Per-customer limit', default=0)
    budget_cap = fields.Float('Discount budget cap', default=0.0,
        help='0 = unlimited. Auto-ends when the spent discount reaches it.')
    usage_count = fields.Integer('Times used', default=0, readonly=True)
    budget_spent = fields.Float('Budget spent', default=0.0, readonly=True)

    # ── المكافآت (Rewards) ───────────────────────────────────────────
    reward_free_ship = fields.Boolean('🚚 Free shipping reward', default=False)
    reward_gift_product_id = fields.Many2one(
        'product.product', string='🎁 Mandatory free gift')
    reward_gift_qty = fields.Integer('Gift qty', default=1)
    reward_gift_threshold = fields.Float('Gift cart minimum', default=0.0,
        help='Add the free gift once the cart subtotal reaches this.')
    reward_coupon_mode = fields.Selection([
        ('none',     'No coupon'),
        ('apply',    'Force-apply a coupon program'),
        ('generate', 'Generate a coupon for next order'),
    ], default='none', string='🎟️ Coupon reward')
    reward_coupon_program_id = fields.Many2one(
        'loyalty.program', string='Coupon program')
    reward_loyalty_multiplier = fields.Float('⭐ Loyalty points ×', default=1.0)

    # ── الشروط (Conditions) — تُقيَّم على السلة لبوابة المكافآت ───────
    cond_min_subtotal = fields.Float('Min cart subtotal', default=0.0)
    cond_min_qty = fields.Integer('Min items in cart', default=0)
    cond_first_order = fields.Boolean('First order only', default=False)
    cond_days = fields.Selection([
        ('all', 'Every day'),
        ('weekend', 'Weekends (Fri–Sat)'),
        ('weekdays', 'Weekdays (Sun–Thu)'),
    ], default='all', string='Active days')
    cond_hour_from = fields.Float('Happy hour from', default=0.0,
        help='0–24. Leave from=to=0 for all day.')
    cond_hour_to = fields.Float('Happy hour to', default=0.0)

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

    # ── الاستهداف بالقواعد + حارس الربح ──────────────────────────────
    def _scope_domain(self):
        """Build a product.template domain from the include scopes minus the
        exclude scopes. Empty include set ⇒ matches nothing."""
        self.ensure_one()
        base = [('is_published', '=', True), ('sale_ok', '=', True)]
        inc, exc = [], []
        for s in self.scope_ids:
            leaf = s._leaf()
            if not leaf:
                continue
            (exc if s.kind == 'exclude' else inc).append(leaf)
        if not inc:
            return None
        # OR the includes together
        dom = list(base)
        if len(inc) == 1:
            dom += inc[0]
        else:
            dom += ['|'] * (len(inc) - 1)
            for leaf in inc:
                dom += leaf
        # AND-NOT each exclude
        for leaf in exc:
            if len(leaf) == 1:
                f, op, v = leaf[0]
                neg = {'=': '!=', 'in': 'not in', 'child_of': 'not in'}.get(op)
                if neg:
                    dom.append((f, neg, v))
        return dom

    @api.depends('scope_ids', 'scope_ids.scope_type', 'global_discount_pct',
                 'min_margin_pct', 'margin_guard', 'target_mode',
                 'margin_reserve_ship', 'margin_ship_cost',
                 'min_show_discount_pct', 'margin_mode')
    def _compute_targeted(self):
        for p in self:
            t = e = bm = 0
            if p.target_mode == 'rules':
                dom = p._scope_domain()
                if dom:
                    prods = self.env['product.template'].sudo().search(dom)
                    for pr in prods:
                        guarded = p._guarded_discount(pr, p.global_discount_pct)
                        eff = p._effective_discount(pr, p.global_discount_pct)
                        if eff is not None and eff > 0:
                            t += 1
                        else:
                            e += 1
                            # استُبعِد تحديداً بسبب ضعف الخصم (لا بسبب الربح)
                            if guarded is not None and guarded > 0:
                                bm += 1
            p.targeted_count = t
            p.excluded_count = e
            p.below_min_count = bm

    def _ship_reserve(self):
        """مبلغ التوصيل الذي يُضاف للتكلفة عند حجز ربح التوصيل المجاني."""
        self.ensure_one()
        if self.margin_reserve_ship:
            return max(0.0, self.margin_ship_cost or 0.0)
        return 0.0

    def _margin_pct(self, product):
        lp = product.list_price or 0.0
        if lp <= 0:
            return None
        cost = (product.sudo().standard_price or 0.0) + self._ship_reserve()
        return (lp - cost) / lp * 100.0

    def _guarded_discount(self, product, requested_pct):
        """Return the discount % to apply, respecting the profit floor.
        None ⇒ the product cannot meet the floor → exclude it."""
        self.ensure_one()
        req = max(0.0, float(requested_pct or 0.0))
        # قاعدة عامة: لا يُدرج أي منتج بلا تكلفة معروفة ضمن الخصم — لا نعرف
        # ربحه فلا نخصمه (يُستبعد سواء كان حارس الهامش مفعّلاً أم لا).
        if (product.sudo().standard_price or 0.0) <= 0.0:
            return None
        if not self.margin_guard:
            return req
        lp = product.list_price or 0.0
        # التكلفة الفعلية = تكلفة المنتج + مبلغ التوصيل المحجوز (إن فُعّل)
        cost = (product.sudo().standard_price or 0.0) + self._ship_reserve()
        if lp <= 0:
            return req if not cost else None
        # max discount that still leaves min_margin_pct profit:
        # (lp*(1-d) - cost)/(lp*(1-d)) >= m  ⇒  d <= 1 - cost/(lp*(1-m))
        m = max(0.0, min(0.95, self.min_margin_pct / 100.0))
        denom = lp * (1.0 - m)
        if denom <= 0:
            return None
        max_d = (1.0 - cost / denom) * 100.0
        if max_d <= 0:
            return None                      # even 0% discount breaks floor
        if self.margin_mode == 'derive':
            return round(min(req if req else max_d, max_d), 2)
        return round(min(req, max_d), 2)     # 'cap'

    def _effective_discount(self, product, requested_pct):
        """الخصم الفعلي المعروض للزبون: محميٌّ بحارس الربح **و** فوق الحد
        الأدنى للخصم المعروض. None ⇒ المنتج يُستبعَد من العرض.

        نقطة القرار الموحَّدة المستخدَمة في كل مكان (البادج/سعر الكرت،
        توليد الأسطر، العدّادات، أعمدة الربحية) حتى لا تتعارض الحسابات."""
        self.ensure_one()
        d = self._guarded_discount(product, requested_pct)
        if d is None or d <= 0:
            return None
        floor = self.min_show_discount_pct or 0.0
        if floor and d < floor:
            return None                      # خصم ضعيف → يُستبعَد من العرض
        return d

    def action_generate_lines(self):
        """Rules mode: (re)build margin-guarded admin lines from the scopes.
        Existing vendor lines are kept; previously auto-generated lines are
        refreshed."""
        Line = self.env['mobile.promotion.line'].sudo()
        for p in self:
            if p.target_mode != 'rules' or p._is_capped():
                continue
            dom = p._scope_domain()
            prods = self.env['product.template'].sudo().search(dom) \
                if dom else self.env['product.template'].browse([])
            keep = set()
            for pr in prods:
                d = p._effective_discount(pr, p.global_discount_pct)
                if d is None or d <= 0:
                    continue
                keep.add(pr.id)
                existing = Line.search([('promotion_id', '=', p.id),
                                        ('product_tmpl_id', '=', pr.id)],
                                       limit=1)
                vals = {'discount_pct': d, 'state': 'approved',
                        'auto_generated': True}
                if existing:
                    if existing.auto_generated:
                        existing.write(vals)
                else:
                    Line.create(dict(vals, promotion_id=p.id,
                                     product_tmpl_id=pr.id))
            # drop stale auto lines no longer targeted
            Line.search([('promotion_id', '=', p.id),
                         ('auto_generated', '=', True),
                         ('product_tmpl_id', 'not in', list(keep))]).unlink()
        return True

    # ── تقييم الشروط على السلة ───────────────────────────────────────
    def _conditions_met(self, order):
        """True when this promo's cart-level conditions hold for `order`.
        Gates the order-level rewards (gift / free-ship / coupon)."""
        self.ensure_one()
        if self.cond_min_subtotal and (order.amount_untaxed or 0.0) \
                < self.cond_min_subtotal:
            return False
        if self.cond_min_qty:
            q = sum(l.product_uom_qty for l in order.order_line
                    if not l.display_type
                    and not getattr(l, 'uellow_promo_gift', False))
            if q < self.cond_min_qty:
                return False
        if self.cond_first_order and order.partner_id:
            prior = self.env['sale.order'].sudo().search_count([
                ('partner_id', '=', order.partner_id.id),
                ('state', 'in', ('sale', 'done')),
                ('id', '!=', order.id)])
            if prior:
                return False
        if self.cond_days and self.cond_days != 'all' \
                or self.cond_hour_from or self.cond_hour_to:
            now = fields.Datetime.context_timestamp(
                self, fields.Datetime.now())
            wd = now.weekday()                    # Mon=0 … Sun=6
            is_weekend = wd in (4, 5)             # الجمعة والسبت
            if self.cond_days == 'weekend' and not is_weekend:
                return False
            if self.cond_days == 'weekdays' and is_weekend:
                return False
            if self.cond_hour_from or self.cond_hour_to:
                h = now.hour + now.minute / 60.0
                lo = self.cond_hour_from or 0.0
                hi = self.cond_hour_to or 24.0
                if not (lo <= h <= hi):
                    return False
        return True

    # ── مكافآت السلة (تُستهلَك من cart.py) ───────────────────────────
    @api.model
    def cart_rewards(self, order, channel='mobile'):
        """Resolve the order-level rewards from the running promotions that
        match this cart's channel + website. Returns a plain dict:
        {free_ship: bool, gift: (product_id, qty, promo_id)|None,
         coupon_program_id: int|None, loyalty_x: float}."""
        now = fields.Datetime.now()
        chans = {
            'mobile':  ('mobile', 'both', 'pos'),
            'website': ('website', 'both', 'pos'),
        }.get(channel, ('mobile', 'both', 'website', 'pos'))
        promos = self.sudo().search([
            ('state', '=', 'running'), ('active', '=', True),
            ('date_from', '<=', now), ('date_to', '>=', now),
            ('channel', 'in', list(chans)),
        ], order='priority desc, id')
        wid = order.website_id.id if order.website_id else None
        partner = order.partner_id
        subtotal = order.amount_untaxed or 0.0
        out = {'free_ship': False, 'gift': None, 'coupon_program_id': None,
               'loyalty_x': 1.0, 'promo_ids': []}
        for p in promos:
            if p.website_ids and wid and wid not in p.website_ids.ids:
                continue
            if p._is_capped(partner):          # سقوف: استخدام/عميل/ميزانية
                continue
            if not p._conditions_met(order):   # شروط السلة
                continue
            used = False
            if p.reward_free_ship:
                out['free_ship'] = True; used = True
            if (p.reward_gift_product_id and not out['gift']
                    and subtotal >= (p.reward_gift_threshold or 0.0)):
                out['gift'] = (p.reward_gift_product_id.id,
                               max(1, p.reward_gift_qty or 1), p.id); used = True
            if (p.reward_coupon_mode == 'apply'
                    and p.reward_coupon_program_id
                    and not out['coupon_program_id']):
                out['coupon_program_id'] = p.reward_coupon_program_id.id
                used = True
            if (p.reward_loyalty_multiplier or 1.0) > out['loyalty_x']:
                out['loyalty_x'] = p.reward_loyalty_multiplier
            if used:
                out['promo_ids'].append(p.id)
        return out

    # ── السقوف + التسجيل + توليد الكوبون ─────────────────────────────
    def _is_capped(self, partner=None):
        """True when this promo hit a usage / budget / per-customer cap."""
        self.ensure_one()
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return True
        if self.budget_cap and self.budget_spent >= self.budget_cap:
            return True
        if partner and self.per_customer_limit:
            n = self.env['mobile.promo.usage'].sudo().search_count([
                ('promotion_id', '=', self.id),
                ('partner_id', '=', partner.id)])
            if n >= self.per_customer_limit:
                return True
        return False

    def _register_use(self, order, amount=0.0):
        """Record one use of each promo against a confirmed order; bump
        counters; auto-end when a cap is reached; generate post-purchase
        coupons. Best-effort, never raises."""
        Usage = self.env['mobile.promo.usage'].sudo()
        Card = self.env['loyalty.card'].sudo()
        for p in self:
            try:
                if Usage.search_count([('order_id', '=', order.id),
                                       ('promotion_id', '=', p.id)]):
                    continue                    # already counted this order
                Usage.create({'promotion_id': p.id, 'order_id': order.id,
                              'partner_id': order.partner_id.id,
                              'amount': amount})
                p.usage_count = (p.usage_count or 0) + 1
                p.budget_spent = (p.budget_spent or 0.0) + (amount or 0.0)
                # توليد كوبون للطلب القادم
                if (p.reward_coupon_mode == 'generate'
                        and p.reward_coupon_program_id):
                    try:
                        Card.create({
                            'program_id': p.reward_coupon_program_id.id,
                            'partner_id': order.partner_id.id,
                            'points': 1,
                        })
                    except Exception:
                        _logger.debug('coupon generate failed', exc_info=True)
                # إيقاف تلقائي عند بلوغ السقف
                if ((p.usage_limit and p.usage_count >= p.usage_limit)
                        or (p.budget_cap
                            and p.budget_spent >= p.budget_cap)):
                    if p.state == 'running':
                        p.action_end()
            except Exception:
                _logger.debug('promo register_use failed', exc_info=True)

    # ── lifecycle ───────────────────────────────────────────────────
    def action_open(self):
        self.write({'state': 'open'})

    def action_start(self):
        for p in self:
            if p.target_mode == 'rules':
                p.action_generate_lines()
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
            # v2.2.48 — mobile cards only surface mobile-eligible channels.
            ('promotion_id.channel', 'in', ('mobile', 'both', 'pos')),
        ], order='promotion_id', limit=3)
        for l in lines:
            # لا يُخصَم منتج بلا تكلفة معروفة — الحارس النهائي (يشمل أسطر
            # التجار/الإدخال اليدوي) على البادج وعلى سعر الكرت المحسوب.
            if (l.product_tmpl_id.sudo().standard_price or 0.0) <= 0.0:
                continue
            p = l.promotion_id
            if website_id and p.website_ids and \
                    website_id not in p.website_ids.ids:
                continue
            # حارس الهامش يُطبَّق حيًّا بالتكلفة الحالية: السطر المخزّن قد
            # يكون قديماً (تغيّرت التكلفة بعد توليده) فيؤدي لخسارة — هنا
            # نعيد ضبط الخصم على الحد الذي يحفظ أرضية الربح الآن. None ⇒
            # المنتج لا يحقق الأرضية الآن → نتجاوزه (لا خصم ولا بادج).
            disc = l.discount_pct
            # حارس الربح + الحد الأدنى للخصم المعروض، حيًّا بالتكلفة الحالية.
            if p.margin_guard or p.min_show_discount_pct:
                g = p._effective_discount(l.product_tmpl_id, l.discount_pct)
                if g is None or g <= 0:
                    continue
                disc = g
            return {
                'id': p.id,
                'emoji': p.emoji or '🎯',
                'label': {'en': p.label_en or '', 'ar': p.label_ar or p.label_en or ''},
                'bg': p.bg_color or '#FFF8E1',
                'fg': p.fg_color or '#8B6508',
                'discount_pct': disc,
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
    # v2.2.48 — lines built by the rules engine (refreshable / prunable).
    auto_generated = fields.Boolean('Auto (rules)', default=False, index=True)

    # تفاصيل الربحية (محسوبة، للعرض في تاب المنتجات) ──────────────────
    cost = fields.Float('Cost', compute='_compute_economics',
                        digits='Product Price',
                        help='Product cost (standard_price).')
    eff_discount_pct = fields.Float('Applied %', compute='_compute_economics',
        help='The discount ACTUALLY applied right now: the stored % capped '
             'live to the profit floor at the current cost. Differs from the '
             'stored Discount % when the cost changed after the line was '
             'generated. 0 = the product no longer meets the floor (no '
             'discount shown to customers).')
    price_before = fields.Float('Price (before)', compute='_compute_economics',
                                digits='Product Price',
                                help='Sale price before the promotion discount.')
    price_after = fields.Float('Price (after)', compute='_compute_economics',
                               digits='Product Price',
                               help='Sale price after the APPLIED discount.')
    profit = fields.Float('Profit', compute='_compute_economics',
                          digits='Product Price',
                          help='Gross product profit = price after − cost. '
                               '(Delivery reserve is NOT subtracted here.)')
    profit_pct = fields.Float('Profit %', compute='_compute_economics',
                              help='Gross profit as a % of the after price.')
    net_profit = fields.Float('Net profit', compute='_compute_economics',
        digits='Product Price',
        help='price after − cost − delivery reserve. This is the figure the '
             'margin guard keeps above your Min Profit Margin %.')
    net_profit_pct = fields.Float('Net %', compute='_compute_economics',
        help='Net profit ÷ after price — should always be ≥ your Min Profit '
             'Margin %. Below it ⇒ a stale line (regenerate).')
    is_hidden = fields.Boolean('Hidden 🚫', compute='_compute_economics',
        help='This product is NOT shown to customers right now: its effective '
             'discount fell to 0 (cost too high) or below the "Min discount % '
             'to show" threshold.')
    # rollback bookkeeping for apply_discounts
    price_applied = fields.Boolean(readonly=True)
    old_list_price = fields.Float(readonly=True)
    old_compare_price = fields.Float(readonly=True)

    _sql_constraints = [
        ('uniq_promo_product', 'unique(promotion_id, product_tmpl_id)',
         'This product is already in the promotion.'),
    ]

    @api.depends('product_tmpl_id', 'product_tmpl_id.standard_price',
                 'product_tmpl_id.list_price', 'discount_pct',
                 'promotion_id.margin_guard', 'promotion_id.margin_mode',
                 'promotion_id.min_margin_pct', 'promotion_id.margin_reserve_ship',
                 'promotion_id.margin_ship_cost')
    def _compute_economics(self):
        for l in self:
            tmpl = l.product_tmpl_id
            p = l.promotion_id
            cost = (tmpl.sudo().standard_price or 0.0) if tmpl else 0.0
            before = (tmpl.list_price or 0.0) if tmpl else 0.0
            reserve = p._ship_reserve() if (p and tmpl) else 0.0
            # الخصم الفعّال = المخزّن مقصوصاً حيًّا على أرضية الربح + الحد
            # الأدنى للخصم المعروض، بالتكلفة الحالية (نفس ما يراه الزبون).
            # None ⇒ مُستبعَد من العرض → 0 + is_hidden.
            eff = l.discount_pct or 0.0
            hidden = False
            if p and tmpl and (p.margin_guard or p.min_show_discount_pct):
                g = p._effective_discount(tmpl, l.discount_pct)
                if g is None or g <= 0:
                    eff = 0.0
                    hidden = True
                else:
                    eff = g
            after = round(before * (1.0 - eff / 100.0), 3)
            l.cost = cost
            l.eff_discount_pct = round(eff, 2)
            l.is_hidden = hidden
            l.price_before = before
            l.price_after = after
            l.profit = round(after - cost, 3)
            l.profit_pct = round((after - cost) / after * 100.0, 2) \
                if after else 0.0
            l.net_profit = round(after - cost - reserve, 3)
            l.net_profit_pct = round((after - cost - reserve) / after * 100.0, 2) \
                if after else 0.0

    def action_approve(self):
        self.write({'state': 'approved'})
        for l in self:
            if (l.promotion_id.state == 'running'
                    and l.promotion_id.apply_discounts
                    and not l.price_applied):
                l.promotion_id._apply_prices()

    def action_reject(self):
        self.write({'state': 'rejected'})


class MobilePromoScope(models.Model):
    """v2.2.48 — a targeting scope line: include/exclude a category, brand,
    price range, specific products, or a vendor. The promotion ANDs the
    excludes against the OR of the includes."""
    _name = 'mobile.promo.scope'
    _description = 'Promotion Targeting Scope'
    _order = 'kind desc, id'

    promotion_id = fields.Many2one('mobile.app.promotion', required=True,
                                   ondelete='cascade', index=True)
    kind = fields.Selection([
        ('include', '➕ Include'),
        ('exclude', '➖ Exclude'),
    ], default='include', required=True)
    scope_type = fields.Selection([
        ('category',    '🗂️ Category'),
        ('brand',       '🏷️ Brand'),
        ('price_range', '💵 Price range'),
        ('product',     '📦 Specific products'),
        ('vendor',      '🏪 Vendor'),
        ('all',         '🌐 Whole catalogue'),
    ], default='category', required=True)

    category_id = fields.Many2one('product.public.category', string='Category')
    include_subcats = fields.Boolean('Include sub-categories', default=True)
    brand_id = fields.Many2one('product.brand', string='Brand')
    product_tmpl_ids = fields.Many2many('product.template', string='Products')
    vendor_id = fields.Many2one('uellow.vendor', string='Vendor')
    price_min = fields.Float('Price from')
    price_max = fields.Float('Price to')

    def _leaf(self):
        """Return a domain fragment (list of leaves) for this scope, or
        None when it carries no usable value."""
        self.ensure_one()
        t = self.scope_type
        if t == 'all':
            return [(1, '=', 1)]
        if t == 'category' and self.category_id:
            op = 'child_of' if self.include_subcats else 'in'
            return [('public_categ_ids', op, self.category_id.id)]
        if t == 'brand' and self.brand_id:
            return [('brand_id', '=', self.brand_id.id)]
        if t == 'product' and self.product_tmpl_ids:
            return [('id', 'in', self.product_tmpl_ids.ids)]
        if t == 'vendor' and self.vendor_id \
                and 'vendor_id' in self.env['product.template']._fields:
            return [('vendor_id', '=', self.vendor_id.id)]
        if t == 'price_range' and (self.price_min or self.price_max):
            leaf = []
            if self.price_min:
                leaf.append(('list_price', '>=', self.price_min))
            if self.price_max:
                leaf.append(('list_price', '<=', self.price_max))
            return leaf
        return None


class SaleOrderLinePromoGift(models.Model):
    _inherit = 'sale.order.line'

    # v2.2.48 — سطر هدية إجبارية مُضافة بواسطة محرّك العروض (لا يُحذف يدوياً؛
    # يُزامَن تلقائياً مع أهلية السلة).
    uellow_promo_gift = fields.Boolean('Promo Free Gift', default=False,
                                       index=True, copy=False)
    uellow_promo_id = fields.Many2one('mobile.app.promotion',
                                      ondelete='set null', copy=False)


class MobilePromoUsage(models.Model):
    """v2.2.48 — one row per (promo, order) use — powers usage/per-customer
    caps and the budget meter."""
    _name = 'mobile.promo.usage'
    _description = 'Promotion Usage'
    _order = 'id desc'

    promotion_id = fields.Many2one('mobile.app.promotion', required=True,
                                   ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', index=True)
    order_id = fields.Many2one('sale.order', ondelete='cascade', index=True)
    amount = fields.Float('Discount amount')
    date = fields.Datetime(default=fields.Datetime.now)


class SaleOrderPromoCaps(models.Model):
    _inherit = 'sale.order'

    uellow_promo_ids = fields.Many2many(
        'mobile.app.promotion', 'sale_order_uellow_promo_rel',
        'order_id', 'promo_id', string='Applied Promotions', copy=False)

    def action_confirm(self):
        res = super().action_confirm()
        Promo = self.env['mobile.app.promotion'].sudo()
        for order in self:
            try:
                # العروض المُطبَّقة: المسجّلة من المكافآت + أي عرض جارٍ له سطر
                # على أحد منتجات الطلب.
                promos = order.uellow_promo_ids
                prod_tmpls = order.order_line.mapped(
                    'product_id.product_tmpl_id').ids
                if prod_tmpls:
                    line_promos = self.env['mobile.promotion.line'].sudo().search([
                        ('product_tmpl_id', 'in', prod_tmpls),
                        ('state', '=', 'approved'),
                        ('promotion_id.state', '=', 'running'),
                    ]).mapped('promotion_id')
                    promos |= line_promos
                if not promos:
                    continue
                # ميزانية تقريبية: إجمالي الخصم بالطلب موزّعاً على العروض
                gross = sum((l.price_unit or 0.0) * (l.product_uom_qty or 0.0)
                            for l in order.order_line
                            if not l.display_type)
                net = sum(l.price_subtotal for l in order.order_line
                          if not l.display_type)
                disc = max(0.0, gross - net)
                share = disc / len(promos) if promos else 0.0
                promos._register_use(order, amount=share)
            except Exception:
                _logger.debug('promo caps on confirm failed', exc_info=True)
        return res
