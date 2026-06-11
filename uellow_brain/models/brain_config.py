"""Uellow Brain — central configuration (singleton) + Profit Guard.

EVERY service of the engine and its options live here, so the whole engine
is controlled from one place. Defaults are SAFE/OFF: nothing changes in
production until an admin enables a service. Every consumer reads the
config defensively (get_config + getattr) so turning one service off never
breaks another.
"""
from odoo import api, fields, models


class UellowBrainConfig(models.Model):
    _name = 'uellow.brain.config'
    _description = 'Uellow Brain — Engine Settings'

    name = fields.Char(default='Uellow Brain Settings', readonly=True)

    # ─────────────────────────── GENERAL ───────────────────────────
    enabled = fields.Boolean(
        'Enable Uellow Brain', default=False,
        help='Master switch. OFF = the store behaves exactly as before; '
             'no ranking changes, no tracking, no automated offers.')
    personalization_mode = fields.Selection([
        ('off', 'Off — no tracking'),
        ('members', 'Members only'),
        ('opt_in', 'Opt-in (explicit consent)'),
        ('full', 'Full — members (server) + guests (device cookies)'),
    ], default='off', required=True, string='Personalization mode')
    default_sort_best_match = fields.Boolean(
        'Make "Best Match" the default sort', default=False,
        help='Category pages, search and blocks default to Best Match '
             'instead of Newest.')

    # ──────────────────── BEST MATCH WEIGHTS (0-100) ───────────────
    w_margin = fields.Integer('Weight — profit margin', default=85)
    w_sales = fields.Integer('Weight — real sales (30d)', default=70)
    w_stock = fields.Integer('Weight — availability', default=80)
    w_rating = fields.Integer('Weight — rating/quality', default=50)
    w_fresh = fields.Integer('Weight — freshness', default=30)
    w_affinity = fields.Integer('Weight — customer affinity', default=60)

    # ───────────────────── PROFIT GUARDRAILS ───────────────────────
    cost_field = fields.Char('Cost field', default='standard_price',
        help='Product field used as the COST when computing margin.')
    min_margin_pct = fields.Float('Minimum profit margin %', default=15.0,
        help='No automated discount/flash/coupon/BNPL may push the net '
             'margin below this. Computed: (price - cost)/price.')
    max_auto_discount_pct = fields.Float('Max automatic discount %',
        default=40.0)
    block_below_cost = fields.Boolean('Never sell below cost', default=True)
    guard_when_cost_unknown = fields.Selection([
        ('skip', 'Allow (skip guard when cost is 0/unknown)'),
        ('block', 'Block discounts when cost is 0/unknown'),
    ], default='skip', string='When cost unknown')
    margin_rule_ids = fields.One2many('uellow.brain.margin.rule', 'config_id',
        string='Per-category / per-vendor margin overrides')

    # ─────────────────── Installments (Taly · Deema soon) ───────────
    # v2.2.27 — Uellow uses Taly today; Deema (and others) coming soon.
    bnpl_enabled = fields.Boolean('Enable smart installments', default=False)
    bnpl_provider = fields.Selection([
        ('taly', 'Taly'),
        ('deema', 'Deema (coming soon)'),
        ('both', 'All available')],
        default='taly', string='Installments provider')
    bnpl_fee_pct = fields.Float('BNPL fee %', default=6.5)
    bnpl_fee_fixed = fields.Float('BNPL fixed fee', default=0.25)
    bnpl_fee_payer = fields.Selection([
        ('merchant', 'Merchant pays'), ('customer', 'Customer pays')],
        default='merchant', string='Who pays the BNPL fee')
    bnpl_min_price = fields.Float('Min product price for installments',
        default=15.0)
    bnpl_installments = fields.Integer('Number of installments', default=4)
    bnpl_respect_guard = fields.Boolean(
        'Only offer BNPL when margin absorbs the fee', default=True)

    # ─────────────────── DISCOUNT DISCIPLINE (anti-gaming) ─────────
    dd_enabled = fields.Boolean('Enable discount discipline', default=True)
    dd_max_coupons_per_quarter = fields.Integer(
        'Max win-back coupons / customer / quarter', default=2)
    dd_cooldown_days = fields.Integer('Cooldown between coupons (days)',
        default=30)
    dd_eligibility = fields.Selection([
        ('all', 'Everyone (loose)'),
        ('new_only', 'New customers only'),
        ('exclude_waiters', 'Everyone except serial waiters'),
    ], default='exclude_waiters', string='Coupon eligibility')
    dd_dependency_threshold = fields.Float(
        'Discount-dependency cutoff %', default=60.0,
        help='Customers whose share of discounted purchases exceeds this '
             'stop receiving proactive coupons.')
    dd_prefer_non_price = fields.Boolean(
        'Prefer non-price incentives (points/shipping/value)', default=True)
    dd_enforce_genuine_discount = fields.Boolean(
        'Enforce genuine discounts (compare-at must be a real prior price)',
        default=True)

    # ────────────────────── DIVERSITY ENGINE ──────────────────────
    div_no_repeat = fields.Boolean(
        'No product repeats across a page', default=True)
    div_max_per_brand = fields.Integer('Max items per brand / page',
        default=3)
    div_max_per_category = fields.Integer('Max items per category / page',
        default=6)
    div_exploration_pct = fields.Integer('Exploration % (fresh injection)',
        default=12)
    div_hide_purchased = fields.Boolean(
        'Hide recently purchased (except consumables)', default=True)
    div_offer_freq_cap = fields.Integer('Same offer cap / customer / day',
        default=1)

    # ──────────────────── INTEREST LIFECYCLE ──────────────────────
    il_decay_halflife_days = fields.Integer('Interest half-life (days)',
        default=3)
    il_category_dominance_pct = fields.Integer(
        'Max one-category dominance / page %', default=25)
    il_balanced_interests = fields.Integer('Balanced top interests',
        default=4)
    il_post_purchase_pivot = fields.Boolean(
        'Pivot to accessories after a one-off purchase', default=True)

    # ─────────────────── CONSIDERED PURCHASE ──────────────────────
    cp_save_for_later = fields.Boolean('Save-for-later cart', default=True)
    cp_color_helper = fields.Boolean('Variant decision helper', default=True)
    cp_share_to_decide = fields.Boolean('Share-to-decide (family vote)',
        default=True)
    cp_cart_price_watch = fields.Boolean('Cart price/stock watch',
        default=True)
    cp_reminders = fields.Boolean('Escalating cart reminders', default=True)

    # ─────────────────── PERSONALIZED NOTIFICATIONS ───────────────
    ntf_enabled = fields.Boolean('Enable 1:1 notifications', default=False)
    ntf_respect_prayer = fields.Boolean('Respect prayer times', default=True)
    ntf_golden_hour = fields.Boolean('Send at customer golden hour',
        default=True)
    ntf_freq_cap_per_day = fields.Integer('Notification cap / day', default=1)

    # ──────────────────── REVENUE / LTV SERVICES ──────────────────
    rev_subscriptions = fields.Boolean('Auto-replenish subscriptions',
        default=False)
    rev_warranty_upsell = fields.Boolean('Extended warranty upsell',
        default=False)
    rev_addon_services = fields.Boolean('Add-on services (install/giftwrap)',
        default=False)
    rev_gwp = fields.Boolean('Gift with purchase', default=False)
    rev_oos_substitute = fields.Boolean('Out-of-stock substitution',
        default=True)
    rev_post_purchase_xsell = fields.Boolean('Post-purchase cross-sell',
        default=True)
    rev_fleet_profile = fields.Boolean('Unified taste profile across apps',
        default=False)

    # ──────────────────────── A/B TESTING ─────────────────────────
    ab_enabled = fields.Boolean('Enable A/B test (Best Match vs Newest)',
        default=False)
    ab_split_pct = fields.Integer('% of users on Best Match (vs Newest)',
        default=50)

    # ───────────────────────── SCORING / CRON ───────────────────────
    score_window_days = fields.Integer('Sales window for score (days)',
        default=30)
    last_scored = fields.Datetime('Last score run', readonly=True)
    scored_count = fields.Integer('Products scored', readonly=True)

    # ───────────────────────── helpers ────────────────────────────

    @api.model
    def get_config(self):
        """Return the singleton config row, creating it once if missing.
        Cheap: one indexed read. Callers should sudo()."""
        cfg = self.sudo().search([], limit=1)
        if not cfg:
            cfg = self.sudo().create({})
        return cfg

    @api.model
    def is_on(self, service=None):
        """Master + per-service flag check, fully defensive. Returns False
        on ANY error so a misconfig never breaks a request."""
        try:
            cfg = self.get_config()
            if not cfg.enabled:
                return False
            if service is None:
                return True
            return bool(getattr(cfg, service, False))
        except Exception:
            return False

    def _cost_of(self, product):
        self.ensure_one()
        try:
            return float(getattr(product.sudo(),
                                 self.cost_field or 'standard_price', 0) or 0)
        except Exception:
            return 0.0

    def _min_margin_for(self, product):
        """Per-category / per-vendor override, else global."""
        self.ensure_one()
        try:
            for r in self.margin_rule_ids:
                if r.category_id and r.category_id in product.public_categ_ids:
                    return r.min_margin_pct
            vid = getattr(product, 'vendor_id', False)
            vid = vid.id if vid else 0
            for r in self.margin_rule_ids:
                if r.vendor_ref and vid and r.vendor_ref == vid:
                    return r.min_margin_pct
        except Exception:
            pass
        return self.min_margin_pct

    def guard_price(self, product, proposed_price, extra_fee=0.0):
        """THE profit guard. Returns the safe price ≥ floor, never below
        cost. Used by every automated discount/flash/coupon/BNPL.
        floor = cost × (1 + minMargin%) + extra_fee."""
        self.ensure_one()
        try:
            cost = self._cost_of(product)
            if cost <= 0:
                # cost unknown
                if self.guard_when_cost_unknown == 'block':
                    return float(product.list_price or proposed_price)
                return max(0.0, float(proposed_price))
            floor = cost * (1 + (self._min_margin_for(product) or 0) / 100.0)
            floor += float(extra_fee or 0)
            if self.block_below_cost:
                floor = max(floor, cost + float(extra_fee or 0))
            return max(float(proposed_price), floor)
        except Exception:
            # On any error, never discount below the list price.
            return float(product.list_price or proposed_price)

    # ── notifications timing guard (Phase 5) ───────────────────────
    def notify_allowed_now(self, partner=None):
        """Frequency-cap + quiet-hours gate for 1:1 notifications. Returns
        True if it's OK to send now. Best-effort, never raises."""
        self.ensure_one()
        try:
            if not self.ntf_enabled:
                return False
            from datetime import datetime, timedelta
            # frequency cap: count today's brain notifications to this partner
            if partner:
                Log = self.env.get('uellow.merch.rule.log')
                if Log is not None:
                    day0 = datetime.utcnow().replace(hour=0, minute=0,
                                                     second=0, microsecond=0)
                    sent = Log.sudo().search_count([
                        ('partner_id', '=', partner.id),
                        ('action', '=', 'notify'),
                        ('result', '=', 'ok'),
                        ('create_date', '>=', day0)])
                    if sent >= (self.ntf_freq_cap_per_day or 1):
                        return False
            # prayer-time quiet windows (approx, Gulf): skip the half hour
            # after common adhan slots. Conservative + configurable later.
            if self.ntf_respect_prayer:
                h = datetime.utcnow().hour  # UTC; Kuwait = UTC+3
                kw = (h + 3) % 24
                if kw in (4, 12, 15, 18, 19):   # fajr/dhuhr/asr/maghrib/isha hrs
                    return False
            return True
        except Exception:
            return True

    # ── A/B bucketing (Phase 5) ────────────────────────────────────
    def ab_use_best_match(self, key):
        """Deterministic bucket: True → Best Match, False → Newest. `key`
        = a stable id (partner id / session token / device). Stable per
        user so their experience is consistent."""
        self.ensure_one()
        try:
            if not self.ab_enabled:
                return True
            import hashlib
            h = int(hashlib.md5(str(key or 'guest').encode()).hexdigest(), 16)
            return (h % 100) < (self.ab_split_pct or 50)
        except Exception:
            return True

    # ── "why you saw this" reasons (Phase 5) ───────────────────────
    def why_reasons(self, product, prof=None):
        """Bilingual reasons a product is surfaced — transparency + privacy
        compliance. Cheap, read-only."""
        self.ensure_one()
        out = []
        try:
            if prof and (prof.get('cats')):
                for c in product.public_categ_ids:
                    if str(c.id) in (prof.get('cats') or {}):
                        out.append({'en': 'Matches your interest in %s'
                                    % (c.name or ''),
                                    'ar': 'يطابق اهتمامك بـ%s' % (c.name or '')})
                        break
            if (product.brain_score or 0) >= 60:
                out.append({'en': 'Top-rated pick', 'ar': 'اختيار مميّز'})
            cost = self._cost_of(product)
            price = float(product.list_price or 0)
            if (product.compare_list_price or 0) > price > 0:
                out.append({'en': 'On a real discount',
                            'ar': 'عليه خصم حقيقي'})
            if not out:
                out.append({'en': 'Popular right now', 'ar': 'رائج الآن'})
        except Exception:
            out = [{'en': 'Recommended for you', 'ar': 'مقترح لك'}]
        return out[:3]

    def margin_ok(self, product, price, extra_fee=0.0):
        """True if `price` keeps margin above the red line."""
        self.ensure_one()
        try:
            cost = self._cost_of(product)
            if cost <= 0:
                return self.guard_when_cost_unknown != 'block'
            net = float(price) - cost - float(extra_fee or 0)
            if net <= 0:
                return False
            return (net / float(price)) * 100.0 >= (
                self._min_margin_for(product) or 0)
        except Exception:
            return False


class UellowBrainMarginRule(models.Model):
    _name = 'uellow.brain.margin.rule'
    _description = 'Brain — per-scope minimum margin override'

    config_id = fields.Many2one('uellow.brain.config', ondelete='cascade')
    category_id = fields.Many2one('product.public.category', string='Category')
    # vendor kept as a plain id to avoid hard-coupling Brain to the
    # multivendor module (isolation). Set the uellow.vendor id here.
    vendor_ref = fields.Integer('Vendor id (optional)')
    min_margin_pct = fields.Float('Minimum margin %', default=15.0)
    note = fields.Char('Note')
