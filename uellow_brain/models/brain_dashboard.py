"""Uellow Brain — KPI dashboard (computed on open, never per-request).

A TransientModel whose fields are computed once when the admin opens the
dashboard. Heavy aggregates are cheap SQL run on demand (not on storefront
traffic) so there is zero pressure on the app/server.
"""
from datetime import datetime, timedelta

from odoo import api, fields, models


class UellowBrainDashboard(models.TransientModel):
    _name = 'uellow.brain.dashboard'
    _description = 'Uellow Brain — Dashboard'

    # engine state
    engine_on = fields.Boolean(compute='_compute_kpis')
    mode = fields.Char(compute='_compute_kpis')
    last_scored = fields.Datetime(compute='_compute_kpis')
    scored_count = fields.Integer(compute='_compute_kpis')

    # catalogue
    published_products = fields.Integer(compute='_compute_kpis')
    avg_brain_score = fields.Float(compute='_compute_kpis')
    low_margin_products = fields.Integer(compute='_compute_kpis',
        string='Low-margin products (< red line)')
    below_cost_products = fields.Integer(compute='_compute_kpis')
    no_image_products = fields.Integer(compute='_compute_kpis')

    # commerce (30d)
    revenue_30d = fields.Float(compute='_compute_kpis')
    orders_30d = fields.Integer(compute='_compute_kpis')
    aov_30d = fields.Float(compute='_compute_kpis', string='AOV (30d)')
    units_30d = fields.Integer(compute='_compute_kpis')

    # carts / intent
    open_carts = fields.Integer(compute='_compute_kpis')
    open_cart_value = fields.Float(compute='_compute_kpis')

    # discovery
    searches_30d = fields.Integer(compute='_compute_kpis')
    zero_result_searches = fields.Integer(compute='_compute_kpis')

    # services snapshot
    services_on = fields.Char(compute='_compute_kpis',
        string='Active services')

    def _compute_kpis(self):
        cr = self.env.cr
        Cfg = self.env.get('uellow.brain.config')
        cfg = Cfg.get_config() if Cfg is not None else None
        Tmpl = self.env['product.template'].sudo()
        since = datetime.utcnow() - timedelta(days=30)
        for rec in self:
            # engine
            rec.engine_on = bool(cfg and cfg.enabled)
            rec.mode = (cfg and cfg.personalization_mode) or 'off'
            rec.last_scored = cfg and cfg.last_scored or False
            rec.scored_count = (cfg and cfg.scored_count) or 0
            # catalogue
            rec.published_products = Tmpl.search_count(
                [('is_published', '=', True), ('sale_ok', '=', True)])
            try:
                cr.execute("SELECT COALESCE(AVG(brain_score),0) "
                           "FROM product_template WHERE is_published=true")
                rec.avg_brain_score = round(cr.fetchone()[0] or 0, 2)
            except Exception:
                rec.avg_brain_score = 0
            # margin health
            low = below = 0
            if cfg:
                try:
                    prods = Tmpl.search([('is_published', '=', True),
                                         ('sale_ok', '=', True)], limit=5000)
                    for p in prods:
                        cost = cfg._cost_of(p)
                        price = float(p.list_price or 0)
                        if cost > 0 and price > 0:
                            if price < cost:
                                below += 1
                            elif ((price - cost) / price) * 100 < \
                                    (cfg.min_margin_pct or 0):
                                low += 1
                except Exception:
                    pass
            rec.low_margin_products = low
            rec.below_cost_products = below
            rec.no_image_products = Tmpl.search_count(
                [('is_published', '=', True), ('image_1920', '=', False)])
            # commerce 30d
            try:
                cr.execute("""
                    SELECT COALESCE(SUM(amount_total),0), COUNT(*)
                    FROM sale_order
                    WHERE date_order >= %s AND state IN ('sale','done')
                """, (since,))
                rev, cnt = cr.fetchone()
                rec.revenue_30d = round(rev or 0, 2)
                rec.orders_30d = int(cnt or 0)
                rec.aov_30d = round((rev / cnt), 2) if cnt else 0.0
            except Exception:
                rec.revenue_30d = rec.orders_30d = rec.aov_30d = 0
            try:
                cr.execute("""
                    SELECT COALESCE(SUM(sol.product_uom_qty),0)
                    FROM sale_order_line sol JOIN sale_order so
                      ON so.id=sol.order_id
                    WHERE so.date_order >= %s AND so.state IN ('sale','done')
                """, (since,))
                rec.units_30d = int(cr.fetchone()[0] or 0)
            except Exception:
                rec.units_30d = 0
            # carts
            try:
                cr.execute("""
                    SELECT COUNT(*), COALESCE(SUM(amount_total),0)
                    FROM sale_order WHERE state='draft'
                """)
                c, v = cr.fetchone()
                rec.open_carts = int(c or 0)
                rec.open_cart_value = round(v or 0, 2)
            except Exception:
                rec.open_carts = rec.open_cart_value = 0
            # discovery
            SA = self.env.get('mobile.search.analytic')
            if SA is not None:
                try:
                    rec.searches_30d = SA.sudo().search_count(
                        [('create_date', '>=', since)])
                    rec.zero_result_searches = SA.sudo().search_count(
                        [('create_date', '>=', since),
                         ('results_count', '=', 0)])
                except Exception:
                    rec.searches_30d = rec.zero_result_searches = 0
            else:
                rec.searches_30d = rec.zero_result_searches = 0
            # services snapshot
            on = []
            if cfg:
                for fld, lbl in [
                    ('default_sort_best_match', 'Best Match'),
                    ('bnpl_enabled', 'Installments'),
                    ('dd_enabled', 'Discount discipline'),
                    ('div_no_repeat', 'Diversity'),
                    ('ntf_enabled', 'Notifications'),
                    ('rev_subscriptions', 'Subscriptions'),
                    ('rev_warranty_upsell', 'Warranty'),
                    ('rev_oos_substitute', 'OOS substitute'),
                ]:
                    if getattr(cfg, fld, False):
                        on.append(lbl)
            rec.services_on = ' · '.join(on) or '—'

    @api.model
    def action_open(self):
        rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.brain.dashboard',
            'res_id': rec.id,
            'view_mode': 'form',
            'target': 'current',
            'name': '🧠 Uellow Brain — Dashboard',
        }

    def action_recompute_scores(self):
        Cfg = self.env.get('uellow.brain.config')
        if Cfg is not None:
            cfg = Cfg.get_config()
            self.env['product.template'].sudo()._brain_compute_scores(cfg)
        return self.action_open()

    # ──────────── rich data for the OWL dashboard (on demand) ──────────
    @api.model
    def get_dashboard_data(self):
        """One bundled payload for the big visual dashboard. Computed on
        demand (admin opens it) → zero storefront pressure. All guarded."""
        cr = self.env.cr
        env = self.env
        Cfg = env.get('uellow.brain.config')
        cfg = Cfg.get_config() if Cfg is not None else None
        Tmpl = env['product.template'].sudo()
        now = datetime.utcnow()
        d30 = now - timedelta(days=30)

        def _rows(sql, params=()):
            """Savepoint-protected → never poisons the outer transaction."""
            try:
                cr.execute('SAVEPOINT bd_main')
                cr.execute(sql, params)
                r = cr.fetchall()
                cr.execute('RELEASE SAVEPOINT bd_main')
                return r
            except Exception:
                try:
                    cr.execute('ROLLBACK TO SAVEPOINT bd_main')
                except Exception:
                    pass
                return []

        def q1(sql, params=()):
            r = _rows(sql, params)
            return r[0][0] if (r and r[0]) else 0

        def safe(fn, default=0):
            """Run ORM code under a savepoint so a failure can't abort the
            whole dashboard transaction."""
            try:
                cr.execute('SAVEPOINT bd_orm')
                v = fn()
                cr.execute('RELEASE SAVEPOINT bd_orm')
                return v
            except Exception:
                try:
                    cr.execute('ROLLBACK TO SAVEPOINT bd_orm')
                except Exception:
                    pass
                return default

        # ── engine + services ──
        services = []
        if cfg:
            for fld, lbl in [
                ('enabled', 'Engine'), ('default_sort_best_match', 'Best Match default'),
                ('bnpl_enabled', 'Installments'), ('dd_enabled', 'Discount discipline'),
                ('div_no_repeat', 'Diversity'), ('il_post_purchase_pivot', 'Interest lifecycle'),
                ('ntf_enabled', 'Notifications'), ('rev_subscriptions', 'Subscriptions'),
                ('rev_warranty_upsell', 'Warranty'), ('rev_oos_substitute', 'OOS substitute'),
                ('rev_post_purchase_xsell', 'Post-purchase x-sell'),
            ]:
                services.append({'name': lbl, 'on': bool(getattr(cfg, fld, False))})

        # ── KPIs ──
        published = Tmpl.search_count([('is_published', '=', True),
                                       ('sale_ok', '=', True)])
        avg_score = round(q1("SELECT COALESCE(AVG(brain_score),0) FROM "
                             "product_template WHERE is_published=true"), 2)
        revenue_30d = round(q1("SELECT COALESCE(SUM(amount_total),0) FROM "
                               "sale_order WHERE date_order>=%s AND state IN "
                               "('sale','done')", (d30,)), 2)
        orders_30d = int(q1("SELECT COUNT(*) FROM sale_order WHERE "
                            "date_order>=%s AND state IN ('sale','done')", (d30,)))
        aov = round(revenue_30d / orders_30d, 2) if orders_30d else 0.0
        units_30d = int(q1("SELECT COALESCE(SUM(sol.product_uom_qty),0) FROM "
                           "sale_order_line sol JOIN sale_order so ON "
                           "so.id=sol.order_id WHERE so.date_order>=%s AND "
                           "so.state IN ('sale','done')", (d30,)))
        open_carts = int(q1("SELECT COUNT(*) FROM sale_order WHERE state='draft'"))
        open_cart_value = round(q1("SELECT COALESCE(SUM(amount_total),0) FROM "
                                   "sale_order WHERE state='draft'"), 2)
        profiles = 0
        TP = env.get('uellow.taste.profile')
        if TP is not None:
            try:
                profiles = TP.sudo().search_count([("data", "!=", "{}")])
            except Exception:
                profiles = 0
        SA = env.get('mobile.search.analytic')
        searches_30d = zero_res = 0
        if SA is not None:
            try:
                searches_30d = SA.sudo().search_count([('create_date', '>=', d30)])
                zero_res = SA.sudo().search_count(
                    [('create_date', '>=', d30), ('results_count', '=', 0)])
            except Exception:
                pass

        # ── margin health (sample, cost-driven) ──
        healthy = low = below = unknown = 0
        if cfg:
            def _margin_scan():
                h = lo = be = un = 0
                for p in Tmpl.search([('is_published', '=', True),
                                      ('sale_ok', '=', True)], limit=4000):
                    cost = cfg._cost_of(p)
                    price = float(p.list_price or 0)
                    if cost <= 0 or price <= 0:
                        un += 1
                    elif price < cost:
                        be += 1
                    elif ((price - cost) / price) * 100 < (cfg.min_margin_pct or 0):
                        lo += 1
                    else:
                        h += 1
                return (h, lo, be, un)
            healthy, low, below, unknown = safe(_margin_scan, (0, 0, 0, 0))

        # ── score distribution buckets ──
        buckets = [0, 0, 0, 0, 0]
        for b, c in _rows("""
                SELECT width_bucket(brain_score,0,100,5) b, COUNT(*)
                FROM product_template WHERE is_published=true
                GROUP BY b ORDER BY b"""):
            idx = min(max((b or 1) - 1, 0), 4)
            buckets[idx] += int(c)

        # ── revenue/orders last 14 days ──
        rev_series, ord_series = [], []
        for d, rev, c in _rows("""
                SELECT to_char(date_order,'MM-DD') d,
                       COALESCE(SUM(amount_total),0), COUNT(*)
                FROM sale_order
                WHERE date_order >= %s AND state IN ('sale','done')
                GROUP BY 1 ORDER BY MIN(date_order)""",
                (now - timedelta(days=14),)):
            rev_series.append({'label': d, 'value': round(rev or 0, 2)})
            ord_series.append({'label': d, 'value': int(c or 0)})

        # ── top eCommerce categories by avg brain score ──
        def _topcats():
            rg = Tmpl.read_group(
                [('is_published', '=', True), ('public_categ_ids', '!=', False)],
                ['brain_score:avg'], ['public_categ_ids'], limit=8)
            res = []
            for g in rg:
                lbl = g.get('public_categ_ids')
                name = lbl[1] if isinstance(lbl, (list, tuple)) else str(lbl)
                res.append({'name': name,
                            'value': round(g.get('brain_score') or 0, 1)})
            res.sort(key=lambda x: -x['value'])
            return res
        top_cats = safe(_topcats, [])

        # ── top products ──
        top_products = []
        def _topprod():
            res = []
            for p in Tmpl.search([('is_published', '=', True)],
                                 order='brain_score desc', limit=10):
                res.append({'name': (p.name or '')[:42],
                            'score': round(p.brain_score or 0, 1),
                            'price': round(p.list_price or 0, 3)})
            return res
        top_products = safe(_topprod, [])

        # ── top searches ──
        top_searches = []
        if SA is not None:
            top_searches = [{'name': r[0], 'value': int(r[1])} for r in _rows(
                """SELECT keyword, COUNT(*) c FROM mobile_search_analytic
                   WHERE keyword IS NOT NULL AND keyword NOT LIKE '[barcode]%%'
                     AND create_date >= %s
                   GROUP BY keyword ORDER BY c DESC LIMIT 8""", (d30,))]

        return {
            'engine': {
                'on': bool(cfg and cfg.enabled),
                'mode': (cfg and cfg.personalization_mode) or 'off',
                'default_best_match': bool(cfg and cfg.default_sort_best_match),
                'last_scored': (cfg and cfg.last_scored
                                and cfg.last_scored.strftime('%Y-%m-%d %H:%M'))
                               or '—',
                'scored_count': (cfg and cfg.scored_count) or 0,
            },
            'services': services,
            'kpis': {
                'published': published, 'avg_score': avg_score,
                'revenue_30d': revenue_30d, 'orders_30d': orders_30d,
                'aov': aov, 'units_30d': units_30d,
                'open_carts': open_carts, 'open_cart_value': open_cart_value,
                'profiles': profiles, 'searches_30d': searches_30d,
                'zero_res': zero_res,
            },
            'margin': {'healthy': healthy, 'low': low, 'below': below,
                       'unknown': unknown},
            'score_buckets': buckets,
            'rev_series': rev_series, 'ord_series': ord_series,
            'top_cats': top_cats, 'top_products': top_products,
            'top_searches': top_searches,
            'extra': self._dash_extra(cfg),
            'config': self._dash_config(cfg),
        }

    def _safe_orm(self, fn, default=0):
        """Run ORM code under a savepoint so a failure can't abort the
        dashboard transaction."""
        cr = self.env.cr
        try:
            cr.execute('SAVEPOINT bd_safe')
            v = fn()
            cr.execute('RELEASE SAVEPOINT bd_safe')
            return v
        except Exception:
            try:
                cr.execute('ROLLBACK TO SAVEPOINT bd_safe')
            except Exception:
                pass
            return default

    def _dash_extra(self, cfg):
        """v2.2.26 — a much wider set of KPIs/series (all guarded)."""
        cr = self.env.cr
        env = self.env
        now = datetime.utcnow()
        d30 = now - timedelta(days=30)
        Tmpl = env['product.template'].sudo()

        def rows(sql, params=()):
            """Savepoint-protected raw query → fetchall, or [] on error
            WITHOUT poisoning the outer transaction."""
            try:
                cr.execute('SAVEPOINT brain_dash')
                cr.execute(sql, params)
                r = cr.fetchall()
                cr.execute('RELEASE SAVEPOINT brain_dash')
                return r
            except Exception:
                try:
                    cr.execute('ROLLBACK TO SAVEPOINT brain_dash')
                except Exception:
                    pass
                return []

        def q1(sql, params=()):
            r = rows(sql, params)
            return r[0][0] if (r and r[0]) else 0

        # catalogue value + scored count (list_price/brain_score are real
        # columns; image_1920 & standard_price are NOT, so use the ORM).
        cat_value = 0.0
        scored = 0
        r = rows("""SELECT COALESCE(SUM(list_price),0),
                      COUNT(*) FILTER (WHERE brain_score>0)
                      FROM product_template
                      WHERE is_published=true AND sale_ok=true""")
        if r:
            cat_value, scored = r[0]
        def _with_img():
            return Tmpl.search_count([('is_published', '=', True),
                                      ('image_1920', '!=', False)])
        with_img = self._safe_orm(_with_img, 0)
        # inventory cost value via ORM stock_quant (standard_price is
        # company-dependent → not a plain column).
        cost_value = 0.0
        def _stockcost():
            tot = 0.0
            Q = self.env.get('stock.quant')
            if Q is None:
                return 0.0
            for q in Q.sudo().search([('location_id.usage', '=', 'internal')],
                                     limit=8000):
                tot += (q.quantity or 0) * (q.product_id.standard_price or 0)
            return round(tot, 2)
        cost_value = self._safe_orm(_stockcost, 0.0)

        # sessions (guarded)
        members = guests = active_now = 0
        S = env.get('mobile.session')
        if S is not None:
            try:
                members = S.sudo().search_count([('is_guest', '=', False)])
                guests = S.sudo().search_count([('is_guest', '=', True)])
                active_now = S.sudo().search_count([
                    ('last_activity', '>=', now - timedelta(minutes=30))])
            except Exception:
                pass

        # engagement
        wishlist = q1("SELECT COUNT(*) FROM mobile_wishlist") \
            if env.get('mobile.wishlist') is not None else 0
        reviews = q1("SELECT COUNT(*) FROM rating_rating WHERE consumed=true")
        avg_rating = round(q1("SELECT COALESCE(AVG(rating),0) FROM rating_rating "
                              "WHERE consumed=true AND rating>0"), 2)

        # merchandising assets
        def cnt(model, dom):
            m = env.get(model)
            try:
                return m.sudo().search_count(dom) if m is not None else 0
            except Exception:
                return 0
        # is_live is non-stored → search by the underlying stored date fields.
        _now = datetime.now()
        flash_active = cnt('mobile.flash.sale', [
            ('active', '=', True),
            '|', ('start_date', '=', False), ('start_date', '<=', _now),
            '|', ('end_date', '=', False), ('end_date', '>=', _now)])
        promos_active = cnt('mobile.app.promotion', [('state', '=', 'running')])
        bundles_pub = cnt('uellow.bundle', [('state', '=', 'published')])
        freeship_rules = cnt('uellow.freeship.rule', [('active', '=', True)])
        merch_rules = cnt('uellow.merch.rule', [('active', '=', True)])
        merch_fired = q1("SELECT COUNT(*) FROM uellow_merch_rule_log "
                         "WHERE create_date >= %s", (d30,)) \
            if env.get('uellow.merch.rule.log') is not None else 0

        # lifecycle
        new_cust_30d = q1("""SELECT COUNT(*) FROM res_partner p
            WHERE p.create_date>=%s AND p.customer_rank>0""", (d30,))
        abandoned_24h = q1("""SELECT COUNT(*) FROM sale_order
            WHERE state='draft' AND write_date<=%s AND amount_total>0""",
                           (now - timedelta(hours=24),))

        # orders 14d series (savepoint-safe)
        ord14 = [{'label': r[0], 'value': int(r[1])} for r in rows(
            """SELECT to_char(date_order,'MM-DD'), COUNT(*)
               FROM sale_order WHERE date_order>=%s AND state IN ('sale','done')
               GROUP BY 1 ORDER BY MIN(date_order)""",
            (now - timedelta(days=14),))]

        # taste interest distribution (top categories across profiles)
        taste_int = []
        TP = env.get('uellow.taste.profile')
        if TP is not None:
            try:
                from collections import Counter
                import json as _j
                cc = Counter()
                for r in TP.sudo().search([('data', '!=', '{}')], limit=2000):
                    try:
                        for cid in (_j.loads(r.data or '{}').get('cats') or {}):
                            cc[int(cid)] += 1
                    except Exception:
                        pass
                Cat = env['product.public.category'].sudo()
                for cid, n in cc.most_common(8):
                    taste_int.append({'name': Cat.browse(cid).name or str(cid),
                                      'value': n})
            except Exception:
                pass

        return {
            'catalog_value': round(cat_value or 0, 2),
            'stock_cost_value': round(cost_value or 0, 2),
            'scored_pct': round((scored / max(1, self.env['product.template']
                                 .sudo().search_count([('is_published', '=', True)])) * 100), 1),
            'with_image': int(with_img or 0),
            'members': members, 'guests': guests, 'active_now': active_now,
            'wishlist': wishlist, 'reviews': reviews, 'avg_rating': avg_rating,
            'flash_active': flash_active, 'promos_active': promos_active,
            'bundles_pub': bundles_pub, 'freeship_rules': freeship_rules,
            'merch_rules': merch_rules, 'merch_fired_30d': merch_fired,
            'new_cust_30d': new_cust_30d, 'abandoned_24h': abandoned_24h,
            'ord14': ord14, 'taste_int': taste_int,
        }

    def _dash_config(self, cfg):
        """Full settings snapshot so the dashboard shows EVERY capability/
        option at a glance."""
        if not cfg:
            return []
        groups = [
            ('General', [('Engine', cfg.enabled), ('Mode', cfg.personalization_mode),
                         ('Best Match default', cfg.default_sort_best_match)]),
            ('Best Match weights', [('Margin', cfg.w_margin), ('Sales', cfg.w_sales),
                         ('Stock', cfg.w_stock), ('Rating', cfg.w_rating),
                         ('Fresh', cfg.w_fresh), ('Affinity', cfg.w_affinity)]),
            ('Profit guard', [('Cost field', cfg.cost_field),
                         ('Min margin %', cfg.min_margin_pct),
                         ('Max auto discount %', cfg.max_auto_discount_pct),
                         ('Block below cost', cfg.block_below_cost)]),
            ('Installments (Taly)', [('Enabled', cfg.bnpl_enabled), ('Provider', cfg.bnpl_provider),
                         ('Fee %', cfg.bnpl_fee_pct), ('Fixed', cfg.bnpl_fee_fixed),
                         ('Installments', cfg.bnpl_installments),
                         ('Min price', cfg.bnpl_min_price)]),
            ('Discount discipline', [('Enabled', cfg.dd_enabled),
                         ('Max/quarter', cfg.dd_max_coupons_per_quarter),
                         ('Cooldown d', cfg.dd_cooldown_days),
                         ('Eligibility', cfg.dd_eligibility),
                         ('Dependency %', cfg.dd_dependency_threshold),
                         ('Prefer non-price', cfg.dd_prefer_non_price)]),
            ('Diversity', [('No repeat', cfg.div_no_repeat),
                         ('Max/brand', cfg.div_max_per_brand),
                         ('Max/category', cfg.div_max_per_category),
                         ('Exploration %', cfg.div_exploration_pct),
                         ('Hide purchased', cfg.div_hide_purchased)]),
            ('Interest lifecycle', [('Half-life d', cfg.il_decay_halflife_days),
                         ('Dominance %', cfg.il_category_dominance_pct),
                         ('Top interests', cfg.il_balanced_interests),
                         ('Post-purchase pivot', cfg.il_post_purchase_pivot)]),
            ('Considered purchase', [('Save for later', cfg.cp_save_for_later),
                         ('Colour helper', cfg.cp_color_helper),
                         ('Share to decide', cfg.cp_share_to_decide),
                         ('Cart watch', cfg.cp_cart_price_watch),
                         ('Reminders', cfg.cp_reminders)]),
            ('Notifications', [('Enabled', cfg.ntf_enabled),
                         ('Respect prayer', cfg.ntf_respect_prayer),
                         ('Golden hour', cfg.ntf_golden_hour),
                         ('Cap/day', cfg.ntf_freq_cap_per_day)]),
            ('Revenue / LTV', [('Subscriptions', cfg.rev_subscriptions),
                         ('Warranty', cfg.rev_warranty_upsell),
                         ('Add-on services', cfg.rev_addon_services),
                         ('Gift w/ purchase', cfg.rev_gwp),
                         ('OOS substitute', cfg.rev_oos_substitute),
                         ('Post-purchase x-sell', cfg.rev_post_purchase_xsell),
                         ('Fleet profile', cfg.rev_fleet_profile)]),
            ('A/B test', [('Enabled', cfg.ab_enabled),
                         ('Best Match %', cfg.ab_split_pct)]),
        ]
        out = []
        for title, items in groups:
            out.append({'title': title, 'items': [
                {'k': k, 'v': ('✓' if v is True else '✕' if v is False
                               else str(v))} for k, v in items]})
        return out
