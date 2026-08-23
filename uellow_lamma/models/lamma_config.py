# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api


class LammaTier(models.Model):
    _name = 'uellow.lamma.tier'
    _description = 'Lamma Discount Tier'
    _order = 'min_qty, min_amount'

    config_id = fields.Many2one('uellow.lamma.config', ondelete='cascade')
    min_qty = fields.Integer('Min items', default=2)
    min_amount = fields.Float('Min amount', default=0.0)
    discount_pct = fields.Float('Discount %', default=5.0)


class LammaConfig(models.Model):
    _name = 'uellow.lamma.config'
    _description = 'Lamma (لمّة يلو) Settings'

    name = fields.Char(default='لمّة يلو')
    active = fields.Boolean(default=True)

    # --- general ---
    brand_label = fields.Char('Brand label', default='لمّة يلو')
    enable_all_products = fields.Boolean('Enable on all products', default=True)
    replace_add_to_cart = fields.Boolean('Replace "Add to cart" button', default=True)
    min_items = fields.Integer('Min items to activate discount', default=2)
    rounding = fields.Float('Price rounding', default=0.001)
    badge_text = fields.Char('Badge text', default='🧺 وفّر أكثر')

    # --- discount + protection ---
    discount_mode = fields.Selection(
        [('count', 'By item count'), ('amount', 'By amount')],
        default='count', string='Discount mode')
    tier_ids = fields.One2many('uellow.lamma.tier', 'config_id', string='Tiers')
    max_discount_pct = fields.Float('Max discount (cap) %', default=20.0)
    # ── Profit-band engine (all default 0 = OFF; no effect until configured) ──
    min_profit_amount = fields.Float(
        'Min profit / item (amount floor)', default=0.0,
        help='حد أدنى مطلق للربح لكل منتج. الأرضية = الأكبر بين نسبة الهامش والمبلغ.')
    max_margin_pct = fields.Float(
        'Max profit margin % (cap)', default=0.0,
        help='سقف ربح كنسبة. عند تجاوزه يُطبَّق خصم تلقائي. 0 = معطّل.')
    max_profit_amount = fields.Float(
        'Max profit / item (amount cap)', default=0.0,
        help='سقف ربح كمبلغ مطلق لكل منتج. عند تجاوزه يُطبَّق خصم. 0 = معطّل.')
    order_max_profit_amount = fields.Float(
        'Max profit / bundle (order-level cap)', default=0.0,
        help='سقف ربح إجمالي للّمّة كاملة (مبلغ). عند تجاوزه يُخصم الفائض. 0 = معطّل.')
    min_margin_pct = fields.Float('Guaranteed min profit margin %', default=12.0,
                                  help='The dynamic discount is never allowed to push the '
                                       'bundle margin below this floor.')
    partial_discount = fields.Boolean(
        'Discount eligible products only', default=True,
        help='When some products are too thin on margin to discount, apply the '
             'discount to the remaining eligible products instead of zeroing the '
             'whole bundle. Each discounted product still keeps the guaranteed '
             'min margin above.')
    auto_start = fields.Boolean(
        'Auto-start Lamma from cart', default=True,
        help='When ON, the Lamma activates AUTOMATICALLY once the cart has 2+ '
             'products (their cart items appear as a Lamma). When OFF, the '
             'customer must start it manually by adding a product to the Lamma.')

    discount_zero_cost = fields.Boolean(
        'Discount products with no cost', default=True,
        help='Many products have standard_price = 0 (unknown cost). When ON they '
             'are discounted up to the max cap; turn OFF to EXCLUDE zero-cost '
             'products from the discount so an unknown cost can never be sold '
             'below the real one.')

    # --- installment lamma ---
    installment_enabled = fields.Boolean('Enable installment Lamma', default=True)
    installment_extra_margin = fields.Float(
        'Installment guaranteed extra margin %', default=6.5,
        help='Reserved ON TOP of the normal min margin for installment bundles '
             '(covers installment provider fees).')
    installment_provider = fields.Char('Installment provider', default='Tabby / CINET')
    installment_max_months = fields.Integer('Max installments', default=4)
    installment_min_amount = fields.Float('Min bundle amount for installments', default=15.0)

    # --- marketing ---
    suggest_fbt = fields.Boolean('Auto-suggest "frequently bought together"', default=True)
    free_shipping_items = fields.Integer('Free shipping when items >=', default=4)

    # --- availability by country/location ---
    country_ids = fields.Many2many(
        'res.country', string='Enabled countries',
        help='If set, Lamma is offered ONLY in these countries (by the visitor / '
             'website country). Empty = available everywhere.')

    def _country_enabled(self, code):
        """True if Lamma is active for the given ISO country code."""
        self.ensure_one()
        if not self.active:
            return False
        if not self.country_ids:
            return True
        code = (code or '').upper()
        return any((c.code or '').upper() == code for c in self.country_ids)

    # --- coupon program (auto discount on the order total) ---
    def _coupon_program(self):
        """Get/create the 'خصم لمّة يلو' coupons program. A discount reward of
        0.001 currency per point lets each coupon carry an EXACT amount: the
        card's points = the discount in fils (amount × 1000)."""
        LP = self.env['loyalty.program'].sudo()
        prog = LP.search([('name', '=', 'خصم لمّة يلو'),
                          ('program_type', '=', 'coupons')], limit=1)
        if not prog:
            prog = LP.create({
                'name': 'خصم لمّة يلو',
                'program_type': 'coupons',
                'applies_on': 'current',
                'trigger': 'with_code',
                'rule_ids': [(0, 0, {'minimum_amount': 0.0, 'minimum_qty': 0})],
                'reward_ids': [(0, 0, {
                    'reward_type': 'discount',
                    'discount': 0.001,
                    'discount_mode': 'per_point',
                    'discount_applicability': 'order',
                    'description': 'خصم لمّة يلو',
                })],
            })
        return prog

    def _strip_lamma_rewards(self, order, prog):
        """Remove every existing Lamma reward line + coupon + point entry
        from `order` so the discount can never stack across abandoned
        checkouts (idempotent: at most one Lamma discount per order)."""
        from datetime import date, timedelta
        try:
            old_lines = order.order_line.filtered(
                lambda l: l.reward_id and l.reward_id.program_id.id == prog.id)
            coupons = old_lines.mapped("coupon_id")
            if old_lines:
                old_lines.unlink()
            coupons |= order.applied_coupon_ids.filtered(
                lambda c: c.program_id.id == prog.id)
            if coupons:
                order.applied_coupon_ids = [(3, c.id) for c in coupons]
                coupons.sudo().write(
                    {"expiration_date": date.today() - timedelta(days=1)})
            pts = order.coupon_point_ids.filtered(
                lambda pt: pt.coupon_id.program_id.id == prog.id)
            if pts:
                pts.unlink()
        except Exception:
            pass

    def _issue_coupon(self, order, amount, partner=None):
        """Create a one-time discount coupon worth `amount` and apply it to
        `order` (single discount line 'خصم لمّة يلو' on the total, consumed on
        payment). Returns the created loyalty.card (or False)."""
        from datetime import date, timedelta
        amount = round(float(amount or 0.0), 3)
        if amount <= 0:
            return False
        prog = self._coupon_program()
        if not prog:
            return False
        # Never stack Lamma discounts. An abandoned cart used to keep its old
        # Lamma coupon, so a second checkout DOUBLED the discount (a real
        # financial loss). Strip any prior Lamma reward / coupon first.
        self._strip_lamma_rewards(order, prog)
        card = self.env['loyalty.card'].sudo().create({
            'program_id': prog.id,
            'points': round(amount * 1000),  # fils → 0.001/point = exact amount
            'partner_id': (partner or order.partner_id).id,
            'expiration_date': date.today() + timedelta(days=2),
        })
        try:
            res = order._try_apply_code(card.code)
            if isinstance(res, dict) and 'error' not in str(res).lower():
                for coupon, rewards in res.items():
                    for reward in rewards:
                        order._apply_program_reward(reward, coupon)
        except Exception:
            pass
        return card

    # --- KPIs (last 30 days) surfaced on the settings dashboard ---
    kpi_bundles = fields.Integer('Bundles', compute='_compute_kpis')
    kpi_checkouts = fields.Integer('Checkouts', compute='_compute_kpis')
    kpi_conversion = fields.Float('Conversion %', compute='_compute_kpis')
    kpi_discount = fields.Float('Discount issued', compute='_compute_kpis')
    kpi_avg_items = fields.Float('Avg items', compute='_compute_kpis')
    kpi_inst_share = fields.Float('Installment %', compute='_compute_kpis')
    kpi_activity_count = fields.Integer('Activity events', compute='_compute_kpis')

    def _compute_kpis(self):
        A = self.env['uellow.lamma.activity'].sudo()
        for rec in self:
            try:
                s = A.dashboard_stats()
                rec.kpi_bundles = s['bundles']
                rec.kpi_checkouts = s['checkouts']
                rec.kpi_conversion = s['conversion_rate']
                rec.kpi_discount = s['discount_sum']
                rec.kpi_avg_items = s['avg_items']
                rec.kpi_inst_share = round(s['inst_checkouts'] / s['checkouts'] * 100, 1) if s['checkouts'] else 0.0
                rec.kpi_activity_count = A.search_count([])
            except Exception:
                rec.kpi_bundles = rec.kpi_checkouts = rec.kpi_activity_count = 0
                rec.kpi_conversion = rec.kpi_discount = rec.kpi_avg_items = rec.kpi_inst_share = 0.0

    def action_open_activity(self):
        return self.env['ir.actions.act_window']._for_xml_id('uellow_lamma.action_lamma_activity')

    def action_open_stats(self):
        return self.env['ir.actions.act_window']._for_xml_id('uellow_lamma.action_lamma_stats')

    def action_open_coupons(self):
        self.ensure_one()
        prog = self._coupon_program()
        return {
            'type': 'ir.actions.act_window',
            'name': 'كوبونات لمّة يلو',
            'res_model': 'loyalty.card',
            'view_mode': 'list,form',
            'domain': [('program_id', '=', prog.id)] if prog else [('id', '=', 0)],
        }

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
            cfg._seed_default_tiers()
        return cfg

    def _seed_default_tiers(self):
        self.ensure_one()
        if not self.tier_ids:
            self.tier_ids = [
                (0, 0, {'min_qty': 2, 'min_amount': 10, 'discount_pct': 6}),
                (0, 0, {'min_qty': 3, 'min_amount': 20, 'discount_pct': 10}),
                (0, 0, {'min_qty': 4, 'min_amount': 35, 'discount_pct': 14}),
                (0, 0, {'min_qty': 5, 'min_amount': 55, 'discount_pct': 20}),
            ]

    # ------------------------------------------------------------------
    # Pricing engine
    # ------------------------------------------------------------------
    def _tier_pct(self, n_items, amount):
        """Highest tier the bundle qualifies for, by the configured mode."""
        self.ensure_one()
        pct = 0.0
        for t in self.tier_ids.sorted(lambda r: (r.min_qty, r.min_amount)):
            ok = (n_items >= t.min_qty) if self.discount_mode == 'count' else (amount >= t.min_amount)
            if ok:
                pct = t.discount_pct
        return pct

    def _round(self, val):
        r = self.rounding or 0.001
        return round(round(val / r) * r, 3)

    def compute_lamma(self, lines, lamma_type='normal'):
        """Core engine. `lines` = iterable of dicts with 'price' and 'cost'.

        Returns a dict describing the margin-protected price:
          n, subtotal, cost, discount_pct, pays, saved, margin_pct,
          capped (bool — discount was reduced to protect margin),
          floor_margin_pct, monthly (installment only), eligible.
        """
        self.ensure_one()
        lines = [dict(price=float(l['price'] or 0.0), cost=float(l.get('cost', 0.0) or 0.0))
                 for l in lines]
        n = len(lines)
        subtotal = sum(l['price'] for l in lines)
        cost = sum(l['cost'] for l in lines)

        is_inst = lamma_type == 'installment'
        floor_margin = self.min_margin_pct + (self.installment_extra_margin if is_inst else 0.0)

        eligible = n >= max(1, self.min_items)
        # Installment bundles must clear the installment minimum to get a discount.
        if is_inst and subtotal < self.installment_min_amount:
            eligible = False

        pct = min(self._tier_pct(n, subtotal), self.max_discount_pct) if eligible else 0.0
        # Floor is a margin ON THE SELLING PRICE so it matches the reported
        # margin_pct exactly: at the floor, (pays-cost)/pays == floor_margin.
        fm = min(floor_margin, 99.0)

        def _floor_price(c):
            p_pct = c / (1 - fm / 100.0) if fm < 100 else float('inf')
            p_amt = (c + self.min_profit_amount) if self.min_profit_amount else 0.0
            return max(p_pct, p_amt)

        # Per-product headroom = how much each line can be discounted while KEEPING
        # its own floor margin. A thin-margin product (e.g. a phone) yields 0 and is
        # "excluded"; the discount is then spread over the products that can bear it.
        def _headroom(l):
            # zero/unknown-cost guard: optionally treat cost<=0 as non-discountable
            if not self.discount_zero_cost and (l['cost'] or 0.0) <= 0.0:
                return 0.0
            return max(0.0, l['price'] - _floor_price(l['cost']))
        headrooms = [_headroom(l) for l in lines] if eligible else [0.0] * n
        total_headroom = sum(headrooms)
        excluded = sum(1 for h in headrooms if h <= 1e-9) if eligible else 0
        discountable_subtotal = round(
            sum(l['price'] for l, h in zip(lines, headrooms) if h > 1e-9), 3)

        target = subtotal * pct / 100.0                       # ideal tier discount
        max_cap = subtotal * self.max_discount_pct / 100.0    # absolute cap

        if not eligible or subtotal <= 0:
            applied = 0.0
        elif self.partial_discount:
            # margin-safe: never exceed the summed per-product headroom
            applied = min(target, total_headroom, max_cap)
        else:
            # legacy aggregate floor (whole bundle capped together)
            applied = min(target, max(0.0, subtotal - _floor_price(cost)), max_cap)

        # ── optional profit CEILING: pass profit above the cap back to the buyer.
        # Cap binds at whichever limit is reached first (min of %/amount prices),
        # but never below the profit floor. Runs only when a cap is configured. ──
        if subtotal > 0 and (self.max_margin_pct or self.max_profit_amount):
            def _cap_price(l):
                caps = []
                if self.max_margin_pct and self.max_margin_pct < 100:
                    caps.append(l['cost'] / (1 - self.max_margin_pct / 100.0))
                if self.max_profit_amount:
                    caps.append(l['cost'] + self.max_profit_amount)
                return min(caps) if caps else l['price']
            _finals = []
            for l, h in zip(lines, headrooms):
                share = (applied * (h / total_headroom)) if total_headroom > 1e-9 else 0.0
                after_tier = l['price'] - share
                _finals.append(max(_floor_price(l['cost']), min(after_tier, _cap_price(l))))
            _cap_applied = subtotal - sum(_finals)
            if _cap_applied > applied:            # ceiling only ever adds discount
                applied = _cap_applied

        # ── installment ALWAYS reserves an extra guaranteed margin: reduce the
        # discount by an installment fee so an installment Lamma always costs
        # more than the same normal Lamma — even with fat margins or an active
        # profit ceiling (installment keeps installment_extra_margin% more).
        if is_inst and self.installment_extra_margin and applied > 0:
            _fee = (discountable_subtotal or subtotal) * self.installment_extra_margin / 100.0
            applied = max(0.0, applied - _fee)

        pays = self._round(subtotal - applied)
        # ── optional ORDER-level profit ceiling: cap the WHOLE bundle's total
        # profit at an absolute amount; discount the excess down to the summed
        # per-line floors. Runs only when configured. ──
        if self.order_max_profit_amount and (pays - cost) > self.order_max_profit_amount:
            floor_total = sum(_floor_price(l['cost']) for l in lines)
            new_pays = self._round(max(floor_total, cost + self.order_max_profit_amount))
            if new_pays < pays:
                pays = new_pays
                applied = subtotal - pays
        saved = round(subtotal - pays, 3)
        eff_pct = (saved / subtotal * 100.0) if subtotal > 0 else 0.0
        capped = bool(eligible and saved + 1e-6 < target)
        margin_pct = ((pays - cost) / pays * 100.0) if pays > 0 else 0.0
        months = max(1, self.installment_max_months) if is_inst else 1
        return {
            'type': lamma_type,
            'n': n,
            'subtotal': round(subtotal, 3),
            'cost': round(cost, 3),
            'discount_pct': round(eff_pct, 2),
            'pays': pays,
            'saved': saved,
            'margin_pct': round(margin_pct, 2),
            'capped': capped,
            'excluded': excluded,                 # products that couldn't be discounted
            'discountable_n': n - excluded,
            'discountable_subtotal': discountable_subtotal,
            'floor_margin_pct': round(floor_margin, 2),
            'monthly': self._round(pays / months) if is_inst else 0.0,
            'eligible': eligible,
            'free_shipping': n >= self.free_shipping_items if self.free_shipping_items else False,
        }
