"""v2.2.20 — CONDITIONAL free-shipping rules.

The flag system (product / category / tag) answers "WHAT ships free".
These rules answer "WHEN and FOR WHOM": each rule combines a scope
(whole cart, specific products, categories, sellers or a campaign) with
any number of conditions — cart amount, country/website, language, city,
customer age, new-vs-returning, loyalty tier, date window, weekdays.

Anti-leak design:
* Conditions are AND-ed: every set condition must pass, unset = ignored.
* Personal/cart conditions (amount, qty, age, kind, tier, city) can only
  be verified at CHECKOUT — so a rule that uses any of them never lights
  the product "free shipping" badge (no false promises on cards).
* A rule restricted by country/website only badges when the request
  context resolves to that country/website.
* Age conditions FAIL CLOSED: a customer without a birthdate on file
  does not match an age-restricted rule.
"""
from datetime import date, datetime

from odoo import api, fields, models


class ResPartnerBirthdate(models.Model):
    _inherit = 'res.partner'

    # Used by the age condition; the apps can collect it on the profile.
    uellow_birthdate = fields.Date(
        string='Birthdate',
        help='Used by age-restricted free-shipping rules (and future '
             'birthday perks).')


class FreeShippingRule(models.Model):
    _name = 'uellow.freeship.rule'
    _description = 'Conditional Free-Shipping Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10,
        help='Rules are evaluated in order; the first match wins.')
    note = fields.Text('Internal notes')

    # Bilingual label shown to the customer at checkout when this rule
    # grants the free delivery.
    public_label_en = fields.Char('Customer label (EN)',
                                  default='Free delivery')
    public_label_ar = fields.Char('Customer label (AR)',
                                  default='توصيل مجاني')

    # ── WHAT ships free when the rule matches ──────────────────────
    scope = fields.Selection([
        ('cart', '🛒 Whole cart — free delivery'),
        ('products', '📦 Specific products'),
        ('categories', '🗂 Categories (children included)'),
        ('vendors', '🏪 Sellers'),
        ('campaign', '🎯 Campaign products (mobile promotion)'),
    ], default='cart', required=True)
    product_ids = fields.Many2many(
        'product.template', 'freeship_rule_product_rel', string='Products')
    categ_ids = fields.Many2many(
        'product.public.category', 'freeship_rule_categ_rel',
        string='Categories')
    vendor_ids = fields.Many2many(
        'uellow.vendor', 'freeship_rule_vendor_rel', string='Sellers')
    promotion_id = fields.Many2one('mobile.app.promotion',
        string='Campaign',
        help='Approved products of this promotion ship free while the '
             'rule matches.')
    cart_match = fields.Selection([
        ('any', 'ANY covered item in the cart → free delivery'),
        ('all', 'ALL cart items must be covered → free delivery'),
    ], default='any', required=True,
        help='Only for scoped rules (products/categories/sellers/'
             'campaign).')

    # ── CONDITIONS (all set conditions must pass) ──────────────────
    min_amount = fields.Float('Min cart subtotal',
        help='In the COMPANY currency (KWD) — other-currency carts are '
             'converted before comparing. 0 = no minimum.')
    max_amount = fields.Float('Max cart subtotal', help='0 = no maximum.')
    min_qty = fields.Integer('Min cart items', help='0 = no minimum.')
    country_ids = fields.Many2many('res.country',
        'freeship_rule_country_rel', string='Countries',
        help='Empty = every country.')
    website_ids = fields.Many2many('website',
        'freeship_rule_website_rel', string='Websites',
        help='Empty = every website (all 17 country sites).')
    lang = fields.Selection([
        ('any', 'Any language'), ('en', 'English'), ('ar', 'Arabic'),
    ], default='any', required=True, string='App language')
    city_names = fields.Char('Cities',
        help='Comma-separated, case-insensitive CONTAINS match on the '
             'shipping city (e.g. "Salmiya, حولي"). Empty = any city.')
    min_age = fields.Integer('Min age', help='0 = no minimum. A customer '
        'without a birthdate on file does NOT match age conditions.')
    max_age = fields.Integer('Max age', help='0 = no maximum.')
    customer_kind = fields.Selection([
        ('any', 'Everyone'),
        ('new', 'New customers (first order)'),
        ('returning', 'Returning customers'),
        ('logged', 'Logged-in customers only'),
    ], default='any', required=True, string='Customer type')
    loyalty_tier = fields.Selection([
        ('any', 'Any tier'),
        ('silver', 'Silver and above'),
        ('gold', 'Gold and above'),
        ('platinum', 'Platinum only'),
    ], default='any', required=True, string='Loyalty tier (at least)')
    date_from = fields.Datetime('Starts')
    date_to = fields.Datetime('Ends')
    weekdays = fields.Char('Weekdays',
        help='Comma-separated day numbers, 0=Monday … 6=Sunday '
             '(e.g. "4,5" = Friday + Saturday). Empty = every day.')

    badge_safe = fields.Boolean(
        compute='_compute_badge_safe', store=True,
        string='Shows product badge',
        help='ON when the rule has no personal/cart conditions, so the '
             '"Free shipping" badge can safely show on product cards. '
             'Rules with amount/age/customer conditions apply at checkout '
             'only.')
    summary = fields.Char(compute='_compute_summary', string='Conditions')

    @api.depends('min_amount', 'max_amount', 'min_qty', 'min_age',
                 'max_age', 'customer_kind', 'loyalty_tier', 'city_names')
    def _compute_badge_safe(self):
        for r in self:
            r.badge_safe = not (
                r.min_amount or r.max_amount or r.min_qty
                or r.min_age or r.max_age
                or (r.customer_kind or 'any') != 'any'
                or (r.loyalty_tier or 'any') != 'any'
                or (r.city_names or '').strip())

    @api.depends('min_amount', 'country_ids', 'lang', 'customer_kind',
                 'loyalty_tier', 'date_from', 'date_to', 'min_age',
                 'max_age', 'weekdays', 'city_names', 'min_qty')
    def _compute_summary(self):
        for r in self:
            bits = []
            if r.min_amount:
                bits.append('≥ %.3f' % r.min_amount)
            if r.min_qty:
                bits.append('≥ %d items' % r.min_qty)
            if r.country_ids:
                bits.append('/'.join(r.country_ids.mapped('code')))
            if (r.lang or 'any') != 'any':
                bits.append(r.lang.upper())
            if r.city_names:
                bits.append('🏙 %s' % r.city_names)
            if r.min_age or r.max_age:
                bits.append('age %s–%s' % (r.min_age or '·',
                                           r.max_age or '·'))
            if (r.customer_kind or 'any') != 'any':
                bits.append(r.customer_kind)
            if (r.loyalty_tier or 'any') != 'any':
                bits.append('⭐ %s+' % r.loyalty_tier)
            if r.date_from or r.date_to:
                bits.append('📅')
            if (r.weekdays or '').strip():
                bits.append('days %s' % r.weekdays)
            r.summary = ' · '.join(bits) or 'always'

    # ── matching helpers ────────────────────────────────────────────

    def _ctx_match(self, country_code=None, website_id=None,
                   lang=None, now=None):
        """Context conditions: country / website / language / window."""
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.date_from and now < self.date_from:
            return False
        if self.date_to and now > self.date_to:
            return False
        wd = (self.weekdays or '').strip()
        if wd:
            try:
                days = {int(x) for x in wd.replace('،', ',').split(',')
                        if x.strip() != ''}
                if days and now.weekday() not in days:
                    return False
            except Exception:
                pass
        if self.country_ids:
            codes = {c.upper() for c in self.country_ids.mapped('code')}
            if not country_code or country_code.upper() not in codes:
                return False
        if self.website_ids:
            if not website_id or website_id not in self.website_ids.ids:
                return False
        if (self.lang or 'any') != 'any':
            if not lang or not str(lang).lower().startswith(self.lang):
                return False
        return True

    def _partner_match(self, partner, city=None):
        """Personal conditions: age / customer type / tier / city."""
        self.ensure_one()
        if (self.customer_kind or 'any') == 'logged' and not partner:
            return False
        if self.min_age or self.max_age:
            bd = partner and partner.uellow_birthdate
            if not bd:
                return False           # fail closed — no birthdate, no perk
            today = date.today()
            age = today.year - bd.year - (
                (today.month, today.day) < (bd.month, bd.day))
            if self.min_age and age < self.min_age:
                return False
            if self.max_age and age > self.max_age:
                return False
        if (self.customer_kind or 'any') in ('new', 'returning'):
            if not partner:
                return False
            prior = self.env['sale.order'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
            ])
            if self.customer_kind == 'new' and prior > 0:
                return False
            if self.customer_kind == 'returning' and prior == 0:
                return False
        if (self.loyalty_tier or 'any') != 'any':
            if not partner or self._tier_rank(self._tier_of(partner)) < \
                    self._tier_rank(self.loyalty_tier):
                return False
        cities = (self.city_names or '').strip()
        if cities:
            tgt = (city or '').strip().lower()
            if not tgt:
                return False
            wanted = [c.strip().lower() for c in
                      cities.replace('،', ',').split(',') if c.strip()]
            if not any(w in tgt or tgt in w for w in wanted):
                return False
        return True

    @staticmethod
    def _tier_rank(t):
        return {'any': 0, 'none': 0, 'silver': 1,
                'gold': 2, 'platinum': 3}.get(t or 'none', 0)

    def _tier_of(self, partner):
        """Tier from the LIVE loyalty system (loyalty.card points vs the
        uellow.loyalty.program thresholds)."""
        try:
            cards = self.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id)])
            points = sum(cards.mapped('points'))
            prog = self.env['uellow.loyalty.program'].sudo().search(
                [], limit=1)
            if not prog:
                return 'none'
            if points >= (prog.tier_platinum_min or 15000):
                return 'platinum'
            if points >= (prog.tier_gold_min or 5000):
                return 'gold'
            if points >= (prog.tier_silver_min or 1000):
                return 'silver'
        except Exception:
            pass
        return 'none'

    def _covers_template(self, tmpl):
        """Does this rule's scope include the product?"""
        self.ensure_one()
        if self.scope == 'cart':
            return True
        if self.scope == 'products':
            return tmpl.id in self.product_ids.ids
        if self.scope == 'categories':
            for cat in tmpl.public_categ_ids:
                c = cat
                while c:
                    if c.id in self.categ_ids.ids:
                        return True
                    c = c.parent_id
            return False
        if self.scope == 'vendors':
            vid = getattr(tmpl, 'vendor_id', False)
            return bool(vid and vid.id in self.vendor_ids.ids)
        if self.scope == 'campaign':
            if not self.promotion_id:
                return False
            return bool(self.env['mobile.promotion.line'].sudo().search_count([
                ('promotion_id', '=', self.promotion_id.id),
                ('product_tmpl_id', '=', tmpl.id),
                ('state', '=', 'approved'),
            ]))
        return False

    # ── public entry points ─────────────────────────────────────────

    @api.model
    def _request_ctx(self):
        """(country_code, website_id, lang) from the current HTTP
        request, best-effort. Outside a request → (None, None, None)."""
        try:
            from odoo.http import request as req
            if not req:
                return None, None, None
            website = None
            try:
                website = req.env['website'].get_current_website()
            except Exception:
                pass
            wid = website.id if website else None
            cc = None
            try:
                m = req.env['mobile.country.website'].sudo().search(
                    [('website_id', '=', wid)], limit=1)
                cc = m.country_id.code if m else None
            except Exception:
                pass
            lang = None
            try:
                lang = (req.httprequest.headers.get('X-Lang')
                        or req.env.context.get('lang') or '')
            except Exception:
                pass
            return cc, wid, lang
        except Exception:
            return None, None, None

    @api.model
    def _promo_freeship_tmpl_ids(self, badge_safe_only=True):
        """Template ids covered by RUNNING mobile promotions whose
        `🚚 Free shipping reward` is ON. Lets a promotion's free-shipping
        reward light the SAME free-delivery badge / lists / treatment as a
        conditional rule — automatically, with no rule record to create.

        `badge_safe_only` (for card badges/lists): skip promos that carry
        personal/cart conditions (min subtotal/qty/first-order) so the card
        never promises a free shipping the customer might not actually get
        — those still GRANT at checkout (cart_rewards) once the conditions
        hold, mirroring the rule-engine anti-leak design."""
        Promo = self.env.get('mobile.app.promotion')
        Line = self.env.get('mobile.promotion.line')
        if Promo is None or Line is None:
            return []
        now = fields.Datetime.now()
        promos = Promo.sudo().search([
            ('reward_free_ship', '=', True),
            ('state', '=', 'running'),
            ('active', '=', True),
            ('date_from', '<=', now),
            ('date_to', '>=', now),
            # same channel gate as the discount badge — mobile cards/lists
            ('channel', 'in', ('mobile', 'both', 'pos')),
        ])
        if not promos:
            return []
        cc, wid, lang = self._request_ctx()
        ids = set()
        for p in promos:
            if wid and p.website_ids and wid not in p.website_ids.ids:
                continue
            if badge_safe_only and (
                    (p.cond_min_subtotal or 0.0) > 0.0
                    or (p.cond_min_qty or 0) > 0
                    or p.cond_first_order):
                continue
            lines = Line.sudo().search([
                ('promotion_id', '=', p.id),
                ('state', '=', 'approved')])
            ids.update(lines.mapped('product_tmpl_id').ids)
        return list(ids)

    @api.model
    def badge_rules(self):
        """Active badge-safe rules whose CONTEXT matches this request.
        Used for product-card badges and free-shipping product lists."""
        cc, wid, lang = self._request_ctx()
        out = self.browse()
        for r in self.sudo().search([('badge_safe', '=', True),
                                     ('scope', '!=', 'cart')]):
            if r._ctx_match(country_code=cc, website_id=wid, lang=lang):
                out |= r
        return out

    @api.model
    def badge_covers(self, tmpl):
        """True when any badge-safe matching rule covers the product, OR a
        running free-shipping promotion includes it (treated identically)."""
        for r in self.badge_rules():
            if r._covers_template(tmpl):
                return True
        if tmpl.id in self._promo_freeship_tmpl_ids():
            return True
        return False

    @api.model
    def badge_domain_or(self):
        """Extra OR-leaves for product searches (the `free_shipping`
        block source / list filter) from badge-safe matching rules."""
        ors = []
        for r in self.badge_rules():
            if r.scope == 'products' and r.product_ids:
                ors.append(('id', 'in', r.product_ids.ids))
            elif r.scope == 'categories' and r.categ_ids:
                ors.append(('public_categ_ids', 'child_of',
                            r.categ_ids.ids))
            elif r.scope == 'vendors' and r.vendor_ids:
                ors.append(('vendor_id', 'in', r.vendor_ids.ids))
            elif r.scope == 'campaign' and r.promotion_id:
                lines = self.env['mobile.promotion.line'].sudo().search([
                    ('promotion_id', '=', r.promotion_id.id),
                    ('state', '=', 'approved')])
                if lines:
                    ors.append(('id', 'in',
                                lines.mapped('product_tmpl_id').ids))
        # running free-shipping promotions feed the same free-delivery lists
        promo_ids = self._promo_freeship_tmpl_ids()
        if promo_ids:
            ors.append(('id', 'in', promo_ids))
        return ors

    @api.model
    def bar_threshold(self):
        """Lowest `min_amount` among context-matching CART-scope rules
        whose ONLY personal condition is the amount — safe to drive the
        cart progress bar ("add X more for free shipping"). Rules with
        age/customer/tier/city/qty conditions never feed the bar (the
        bar can't verify them, so it must not promise)."""
        cc, wid, lang = self._request_ctx()
        best = None
        for r in self.sudo().search([('scope', '=', 'cart')]):
            if not r.min_amount or r.max_amount or r.min_qty \
                    or r.min_age or r.max_age \
                    or (r.customer_kind or 'any') != 'any' \
                    or (r.loyalty_tier or 'any') != 'any' \
                    or (r.city_names or '').strip():
                continue
            if not r._ctx_match(country_code=cc, website_id=wid, lang=lang):
                continue
            if best is None or r.min_amount < best:
                best = r.min_amount
        return best

    @api.model
    def order_grant(self, order, amount_company=None):
        """The first active rule granting FREE DELIVERY for this order,
        or an empty recordset. Evaluates context + personal + cart
        conditions against the order's shipping address and lines."""
        if not order:
            return self.browse()
        partner = order.partner_id
        # The website PUBLIC partner is "nobody" for personal conditions.
        try:
            if partner and any(u.has_group('base.group_public')
                               for u in partner.user_ids):
                partner = self.env['res.partner'].browse()
        except Exception:
            pass
        ship = order.partner_shipping_id or partner
        cc = ship.country_id.code if ship and ship.country_id else None
        city = ship.city if ship else None
        _rcc, wid, lang = self._request_ctx()
        cc = cc or _rcc

        if amount_company is None:
            amount_company = order.amount_untaxed or 0.0
            try:
                comp_cur = order.company_id.currency_id
                if order.currency_id and comp_cur \
                        and order.currency_id != comp_cur:
                    amount_company = order.currency_id._convert(
                        amount_company, comp_cur, order.company_id,
                        fields.Date.today())
            except Exception:
                pass

        lines = [l for l in order.order_line
                 if l.product_id and not l.display_type
                 and not getattr(l, 'is_reward_line', False)
                 and not getattr(l, 'is_delivery', False)]
        qty = int(sum(l.product_uom_qty for l in lines))

        for r in self.sudo().search([]):
            if not r._ctx_match(country_code=cc, website_id=wid, lang=lang):
                continue
            if r.min_amount and amount_company < r.min_amount:
                continue
            if r.max_amount and amount_company > r.max_amount:
                continue
            if r.min_qty and qty < r.min_qty:
                continue
            if not r._partner_match(partner, city=city):
                continue
            if r.scope == 'cart':
                return r
            if not lines:
                continue
            covered = [r._covers_template(l.product_id.product_tmpl_id)
                       for l in lines]
            hit = any(covered) if r.cart_match == 'any' else all(covered)
            if hit:
                return r
        return self.browse()
