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
    min_margin_pct = fields.Float('Guaranteed min profit margin %', default=12.0,
                                  help='The dynamic discount is never allowed to push the '
                                       'bundle margin below this floor.')

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
        if is_inst and subtotal < self.installment_min_amount:
            eligible = eligible  # still builds; UI may gate installments separately

        pct = min(self._tier_pct(n, subtotal), self.max_discount_pct) if eligible else 0.0
        capped = False
        if eligible and subtotal > 0:
            # Floor is expressed as a margin ON THE SELLING PRICE so it matches the
            # reported margin_pct exactly: at the floor, (pays-cost)/pays == floor_margin.
            fm = min(floor_margin, 99.0)
            floor = cost / (1 - fm / 100.0) if fm < 100 else float('inf')
            if subtotal * (1 - pct / 100.0) < floor:
                allowed = max(0.0, (1 - floor / subtotal) * 100.0)
                if allowed < pct:
                    pct = allowed
                    capped = True

        pays = self._round(subtotal * (1 - pct / 100.0))
        saved = round(subtotal - pays, 3)
        margin_pct = ((pays - cost) / pays * 100.0) if pays > 0 else 0.0
        months = max(1, self.installment_max_months) if is_inst else 1
        return {
            'type': lamma_type,
            'n': n,
            'subtotal': round(subtotal, 3),
            'cost': round(cost, 3),
            'discount_pct': round(pct, 2),
            'pays': pays,
            'saved': saved,
            'margin_pct': round(margin_pct, 2),
            'capped': capped,
            'floor_margin_pct': round(floor_margin, 2),
            'monthly': self._round(pays / months) if is_inst else 0.0,
            'eligible': eligible,
            'free_shipping': n >= self.free_shipping_items if self.free_shipping_items else False,
        }
