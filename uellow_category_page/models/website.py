# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, tools
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    # ── Master + blocks (a setting for everything) ─────────────────────────
    ucp_enabled        = fields.Boolean('Category Page Redesign', default=True)
    ucp_hero_enabled   = fields.Boolean('Category hero (image header)', default=True)
    ucp_hero_image     = fields.Binary('Hero image override')   # optional; else category image
    ucp_breadcrumb_enabled = fields.Boolean('Breadcrumb trail', default=True)
    ucp_ai_enabled     = fields.Boolean('Smart search bar in hero', default=True)
    ucp_ai_placeholder = fields.Char('Search bar placeholder',
                                     default='Search this category…')
    ucp_badges_enabled = fields.Boolean('Hero trust badges', default=True)

    ucp_presets_enabled = fields.Boolean('Quick chips (brands + sort)', default=True)

    ucp_unlock_enabled  = fields.Boolean('Free-shipping unlock bar', default=True)
    ucp_freeship_threshold = fields.Float(
        'Free-shipping threshold (manual)',
        help="Fallback amount for the unlock bar when no free-shipping RULE "
             "matches (e.g. 15.000). Leave 0 to rely on the free-shipping engine.")
    ucp_ticker_enabled  = fields.Boolean('Live activity ticker', default=True)
    ucp_ticker_text     = fields.Char('Ticker text (optional override)')
    ucp_flash_enabled   = fields.Boolean('Flash-deals strip (live)', default=True)

    # Card look
    ucp_card_restyle    = fields.Boolean('Restyle product cards (v3c)', default=True)
    ucp_card_badges     = fields.Boolean('Card badges (installments + low-stock)', default=True)

    # ── Helpers used by the template (all REAL data) ───────────────────────
    def _ucp_settings(self):
        """Single dict of toggles for the template (cheap, no extra queries)."""
        self.ensure_one()
        return {
            'on':       self.ucp_enabled,
            'hero':     self.ucp_hero_enabled,
            'crumb':    self.ucp_breadcrumb_enabled,
            'ai':       self.ucp_ai_enabled,
            'ai_ph':    self.ucp_ai_placeholder or 'Search…',
            'badges':   self.ucp_badges_enabled,
            'presets':  self.ucp_presets_enabled,
            'unlock':   self.ucp_unlock_enabled,
            'ticker':   self.ucp_ticker_enabled,
            'restyle':  self.ucp_card_restyle,
        }

    # Default hero gradient palette — each category gets a distinct look out of
    # the box (by id); admins can override per-category later (fields on the
    # product.public.category form).
    _UCP_HERO_PALETTE = [
        ('#11182B', '#3A2F8F', '#EC4899'),
        ('#0F2027', '#203A43', '#2C5364'),
        ('#1A2980', '#26D0CE', ''),
        ('#42275A', '#734B6D', ''),
        ('#0B486B', '#F56217', ''),
        ('#360033', '#0B8793', ''),
        ('#283048', '#859398', ''),
        ('#16222A', '#3A6073', ''),
        ('#5B247A', '#1BCEDF', ''),
        ('#642B73', '#C6426E', ''),
    ]

    def _ucp_hero_style(self, category):
        """Inline CSS gradient for the hero — the category's own colors if set,
        else a deterministic default from the palette (different per category)."""
        self.ensure_one()
        c1 = c2 = c3 = None
        if category:
            c1 = (category.ucp_hero_c1 or '').strip() if 'ucp_hero_c1' in category._fields else ''
            c2 = (category.ucp_hero_c2 or '').strip() if 'ucp_hero_c2' in category._fields else ''
            c3 = (category.ucp_hero_c3 or '').strip() if 'ucp_hero_c3' in category._fields else ''
        if not (c1 and c2):
            pal = self._UCP_HERO_PALETTE
            c1, c2, c3 = pal[(category.id if category else 0) % len(pal)]
        if c3:
            return 'background:linear-gradient(120deg,%s,%s 55%%,%s);' % (c1, c2, c3)
        return 'background:linear-gradient(120deg,%s,%s);' % (c1, c2)

    def _ucp_cat_image(self, category):
        """Hero image URL: admin override → else the REAL category image → ''. """
        self.ensure_one()
        if self.ucp_hero_image:
            return '/web/image/website/%d/ucp_hero_image' % self.id
        if category and category.id:
            return '/web/image/product.public.category/%d/image_512' % category.id
        return ''

    def _ucp_breadcrumb(self, category):
        """REAL ancestor chain Home › … › current category."""
        self.ensure_one()
        ar = (self.env.context.get('lang') or '').startswith('ar')
        out = [{'name': 'الرئيسية' if ar else 'Home', 'url': '/shop'}]
        if category:
            chain, c, guard = [], category, 0
            while c and guard < 8:
                chain.append(c)
                c = c.parent_id
                guard += 1
            for c in reversed(chain):
                out.append({'name': c.name, 'url': '/shop/category/%d' % c.id})
        return out

    def _ucp_top_brands(self, category, limit=6):
        """REAL top brands present in this category subtree, as storefront
        filter shortcuts ({id, attr, name, n}). Empty list if none."""
        self.ensure_one()
        if not category:
            return []
        try:
            pp = (category.sudo().parent_path or '') + '%'
            self.env.cr.execute("""
                SELECT v.id, count(DISTINCT t.id) AS n
                FROM product_public_category c
                JOIN product_public_category_product_template_rel r
                     ON r.product_public_category_id = c.id
                JOIN product_template t
                     ON t.id = r.product_template_id AND t.active AND t.is_published
                JOIN product_template_attribute_line l
                     ON l.product_tmpl_id = t.id
                JOIN product_attribute a ON a.id = l.attribute_id
                JOIN product_attribute_value_product_template_attribute_line_rel lv
                     ON lv.product_template_attribute_line_id = l.id
                JOIN product_attribute_value v
                     ON v.id = lv.product_attribute_value_id
                    AND v.attribute_id = l.attribute_id
                WHERE c.parent_path LIKE %s
                  AND a.name->>'en_US' = 'Brand'
                GROUP BY v.id
                ORDER BY n DESC
                LIMIT %s
            """, (pp, limit))
            rows = self.env.cr.fetchall()
            Val = self.env['product.attribute.value'].sudo()
            out = []
            for vid, n in rows:
                v = Val.browse(vid)
                if not v.exists():
                    continue
                out.append({'id': vid, 'attr': v.attribute_id.id,
                            'name': v.name, 'n': n})
            return out
        except Exception:
            return []

    def _ucp_pulse(self, category):
        """REAL one-line activity for the ticker: new-this-fortnight count, or
        the admin override text, or a neutral fallback (never fake names)."""
        self.ensure_one()
        ar = (self.env.context.get('lang') or '').startswith('ar')
        if self.ucp_ticker_text:
            return self.ucp_ticker_text
        try:
            if category:
                since = fields.Datetime.to_string(datetime.now() - timedelta(days=14))
                n = self.env['product.template'].sudo().search_count([
                    ('public_categ_ids', 'child_of', category.id),
                    ('is_published', '=', True),
                    ('create_date', '>=', since),
                ])
                if n > 0:
                    return ('🆕 %d منتج جديد خلال أسبوعين' % n) if ar \
                        else ('🆕 %d new products in the last 2 weeks' % n)
        except Exception:
            pass
        return '🔥 الأكثر رواجًا الآن' if ar else '🔥 Trending now'

    @tools.ormcache()
    def _ucp_bestseller_ids(self):
        """REAL top-selling product templates (last 90 days, confirmed orders),
        excluding service/delivery lines. Cached (registry-lifetime) → one query
        per build, O(1) membership per card. Empty set on any error."""
        try:
            self.env.cr.execute("""
                SELECT pt.id
                FROM sale_order_line sol
                JOIN sale_order so ON so.id = sol.order_id AND so.state = 'sale'
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE so.date_order >= (now() - interval '90 days')
                  AND pt.is_published
                  AND COALESCE(pt.type, 'consu') <> 'service'
                GROUP BY pt.id
                ORDER BY SUM(sol.product_uom_qty) DESC
                LIMIT 60
            """)
            return frozenset(r[0] for r in self.env.cr.fetchall())
        except Exception:
            return frozenset()

    def _ucp_card_extras(self, product, price):
        """REAL per-card badges, computed safely (never raises → never 500s a
        listing). Returns {} when off or nothing applies.
          inst   = monthly installment amount (price / Taly installments)
          inst_n = number of installments
          low    = remaining qty (only when 1..5 left)"""
        self.ensure_one()
        out = {}
        try:
            if not self.ucp_card_badges:
                return out
            price = float(price or 0.0)
            # installments via the live Taly provider (real config, cached per request)
            consts = self._ucp_consts()
            n = consts['taly_n']
            minamt = consts['taly_min']
            if n and price > 0 and price >= minamt:
                out['inst'] = price / n
                out['inst_n'] = n
            # low-stock urgency (real on-hand qty)
            try:
                qty = product.sudo().qty_available
                if 0 < qty <= 5:
                    out['low'] = int(qty)
            except Exception:
                pass
            # bestseller (real 90-day sales)
            try:
                if product.id in self._ucp_bestseller_ids():
                    out['best'] = True
            except Exception:
                pass
        except Exception:
            return {}
        return out

    def _ucp_consts(self):
        """Per-request cache of the page-CONSTANT config lookups every card
        needs (freeship threshold, loyalty points/KD, Taly installment params,
        rank badge cap). On a listing these are identical for all 20+ cards, so
        without this each card re-queries them — ~54ms of repeated config reads
        per page. Memoised on `request`; falls back to a fresh compute when
        there's no request (cron/shell). Keyed by website id."""
        cache = None
        try:
            if request:
                cache = getattr(request, '_ucp_consts_cache', None)
                if cache is None:
                    cache = {}
                    request._ucp_consts_cache = cache
                if self.id in cache:
                    return cache[self.id]
        except Exception:
            cache = None
        data = {'freeship': 0.0, 'ppk': 0.0, 'taly_n': 0, 'taly_min': 0.0,
                'rank_cap': 3}
        try:
            data['freeship'] = self._ucp_freeship()
        except Exception:
            pass
        try:
            prog = self.env['uellow.loyalty.program'].sudo().search(
                [('active', '=', True)], limit=1)
            data['ppk'] = float(prog.points_per_kd or 0.0) if prog else 0.0
        except Exception:
            pass
        try:
            taly = self.env['payment.provider'].sudo().search(
                [('code', '=', 'taly'), ('state', '!=', 'disabled')], limit=1)
            if taly:
                data['taly_n'] = int(taly.taly_installment_type or 0) or 4
                data['taly_min'] = float(taly.taly_min_order_amount or 0) or 10.0
        except Exception:
            pass
        try:
            cfg = self.env['uellow.rank.config'].sudo().search([], limit=1)
            if cfg:
                data['rank_cap'] = int(cfg.badge_max_rank or 3)
        except Exception:
            pass
        try:
            if cache is not None:
                cache[self.id] = data
        except Exception:
            pass
        return data

    def _ucp_app_card(self, product, price_vals):
        """Everything the APP-style rich card needs, computed once per card and
        fully fail-safe (any error → minimal dict, never 500s a listing).
        Returns a dict consumed by uellow_category_page.ucp_appcard_*:
          disc, save, cur, rating{avg,count}, avail{state,n},
          badges[] (status chips, ordered) · slider[] (perk ticker lines),
          promo{emoji,en,ar,bg,fg}|None, rank{n}|None, trend{dir,pct,lowest}|None,
          video, bundle.
        Each list item carries en/ar so the template picks the live language."""
        self.ensure_one()
        out = {'badges': [], 'slider': []}
        try:
            consts = self._ucp_consts()
            pv = price_vals or {}
            base = float(pv.get('base_price') or 0.0)
            red = float(pv.get('price_reduce') or 0.0)
            disc = int(round((base - red) / base * 100)) if (base and base > red) else 0
            out['disc'] = disc
            out['save'] = (base - red) if disc > 0 else 0.0
            cur = self.sudo().currency_id
            out['cur'] = cur.symbol or ''
            dp = int(cur.decimal_places if cur and cur.decimal_places is not None else 3)
            out['save_txt'] = (('%.' + str(dp) + 'f') % out['save']) if out['save'] else ''
            # rating
            out['rating'] = {'avg': float(product.rating_avg or 0.0),
                             'count': int(product.rating_count or 0)}
            # availability
            avail = {'state': 'ok', 'n': 0}
            try:
                storable = bool(getattr(product, 'is_storable', False))
                qty = float(product.sudo().qty_available or 0.0) if storable else None
                allow_oos = bool(getattr(product, 'allow_out_of_stock_order', False))
                if storable and qty is not None:
                    if qty <= 0 and not allow_oos:
                        avail['state'] = 'out'
                    elif 0 < qty <= 5:
                        avail['state'] = 'low'
                        avail['n'] = int(qty)
            except Exception:
                pass
            out['avail'] = avail
            # free shipping (real engine)
            free = False
            try:
                free = bool(hasattr(product, '_is_free_shipping') and product._is_free_shipping())
            except Exception:
                free = False
            # price trend / lowest (smart connector)
            trend = None
            try:
                Hist = self.env.get('uellow.price.history')
                if Hist is not None:
                    t = Hist.sudo().trend_for(product.id)
                    # Only surface price DROPS (a good, trustworthy signal) +
                    # the lowest flag. Up-spikes are noisy import artifacts and
                    # never shown on a storefront card.
                    if t and (t.get('direction') == 'down' or t.get('is_lowest')):
                        d = 'down' if t.get('direction') == 'down' else None
                        pct = int(round(abs(t.get('change_pct') or 0)))
                        trend = {'dir': d, 'pct': (pct if pct <= 95 else 0),
                                 'lowest': bool(t.get('is_lowest'))}
            except Exception:
                trend = None
            out['trend'] = trend
            # bestseller rank
            rank = None
            try:
                Rank = self.env.get('uellow.product.rank')
                if Rank is not None:
                    r = Rank.sudo().search([('product_tmpl_id', '=', product.id)],
                                           order='rank', limit=1)
                    if r and r.rank:
                        maxr = consts['rank_cap']
                        if r.rank <= maxr:        # only ranks the system badges
                            rank = {'n': int(r.rank)}
                if rank is None and product.id in self._ucp_bestseller_ids():
                    rank = {'n': 0}
            except Exception:
                rank = None
            out['rank'] = rank
            # promo coin
            promo = None
            try:
                Promo = self.env.get('mobile.app.promotion')
                if Promo is not None:
                    promo = Promo.sudo().badge_for(product.id, self.id)
            except Exception:
                promo = None
            out['promo'] = promo
            # video / bundle
            out['video'] = bool(getattr(product, 'has_product_video', False))
            out['bundle'] = bool(getattr(product, 'is_bundle', False))

            # ---- STATUS badges row (ordered) ----
            b = out['badges']
            if avail['state'] == 'out':
                b.append({'cls': 'out', 'en': 'Out', 'ar': 'نفد'})
            elif avail['state'] == 'low':
                b.append({'cls': 'low', 'en': 'Only %s' % avail['n'],
                          'ar': 'باقي %s' % avail['n']})
            else:
                b.append({'cls': 'ok', 'en': 'Available', 'ar': 'متاح'})
            if free:
                b.append({'cls': 'free', 'truck': True, 'en': 'Free ship', 'ar': 'شحن مجاني'})
            if trend and trend.get('lowest'):
                b.append({'cls': 'lowest', 'em': '🔥', 'en': 'Lowest', 'ar': 'أقل سعر'})
            if disc > 0:
                b.append({'cls': 'sale', 'em': '⚡', 'en': 'Sale', 'ar': 'عرض'})
            try:
                fresh = product.create_date and (
                    datetime.now() - product.create_date).days <= 14
                if fresh:
                    b.append({'cls': 'new', 'em': '✨', 'en': 'New', 'ar': 'جديد'})
            except Exception:
                pass

            # ---- PERK slider lines (rotating text+icon) ----
            s = out['slider']
            extras = self._ucp_card_extras(product, red)
            if extras.get('inst'):
                s.append({'ic': '💳',
                          'en': 'Pay %.3f/mo' % extras['inst'],
                          'ar': 'قسّطها %.3f/شهر' % extras['inst']})
            try:
                ppk = consts['ppk']
                pts = int((red or base) * ppk)
                if pts > 0:
                    s.append({'ic': '⭐', 'en': 'Earn +%s points' % pts,
                              'ar': 'اكسب +%s نقطة' % pts})
            except Exception:
                pass
            # shipping perk — real store policy (free for this product, or the
            # live free-over threshold for this website). Keeps the ticker with
            # ≥2 rotating lines on virtually every card.
            try:
                if free:
                    s.append({'ic': '🚚', 'en': 'Free shipping', 'ar': 'شحن مجاني'})
                else:
                    thr = consts['freeship']
                    if thr and thr > 0:
                        tt = ('%d' % thr) if float(thr).is_integer() \
                            else (('%.' + str(dp) + 'f') % thr)
                        s.append({'ic': '🚚',
                                  'en': 'Free shipping over %s %s' % (tt, out['cur']),
                                  'ar': 'شحن مجاني فوق %s %s' % (tt, out['cur'])})
            except Exception:
                pass
            if rank is not None:
                s.append({'ic': '🏆', 'en': 'Best seller', 'ar': 'الأكثر مبيعًا'})
            # real social proof — actual units sold (website sales_count)
            try:
                sold = int(getattr(product, 'sales_count', 0) or 0)
                if sold > 0:
                    s.append({'ic': '✅', 'en': 'Sold %s times' % sold,
                              'ar': 'تم بيعه %s مرة' % sold})
            except Exception:
                pass
        except Exception:
            return {'badges': [{'cls': 'ok', 'en': 'Available', 'ar': 'متاح'}],
                    'slider': [], 'disc': 0, 'save': 0.0, 'cur': '',
                    'rating': {'avg': 0, 'count': 0}, 'avail': {'state': 'ok', 'n': 0},
                    'promo': None, 'rank': None, 'trend': None,
                    'video': False, 'bundle': False}
        return out

    def _ucp_flash(self):
        """The live promotion for THIS website, straight from the PROMOTION
        system (mobile.app.promotion): running + in-date + channel reaches the
        website + scoped to this site, highest priority. None if none."""
        self.ensure_one()
        Promo = self.env.get('mobile.app.promotion')
        if Promo is None or not self.ucp_flash_enabled:
            return None
        try:
            ar = (self.env.context.get('lang') or '').startswith('ar')
            now = fields.Datetime.now()
            promos = Promo.sudo().search([
                ('state', '=', 'running'), ('active', '=', True),
                ('date_from', '<=', now), ('date_to', '>=', now),
                ('channel', 'in', ['website', 'both', 'pos']),
            ], order='priority desc, id')
            for p in promos:
                if p.website_ids and self.id not in p.website_ids.ids:
                    continue
                end = ''
                if p.date_to:
                    end = fields.Datetime.to_string(p.date_to).replace(' ', 'T') + 'Z'
                return {
                    'promo_id': p.id,
                    'label': (p.label_ar if ar else p.label_en) or p.name or 'Flash deals',
                    'emoji': p.emoji or '⚡',
                    'pct':   int(p.global_discount_pct or 0),
                    'end':   end,
                    'c1':    p.banner_color_1 or p.bg_color or '',
                    'c2':    p.banner_color_2 or '',
                    'url':   '/flash-deals',
                }
        except Exception:
            return None
        return None

    def _ucp_flash_products(self, promo_id, limit=8):
        """Approved, published products of the promotion — for the desktop
        flash showcase. Each: {name, img, url, before, after, pct}. Price is
        computed from the line discount when the promo is badge-only."""
        self.ensure_one()
        if not promo_id:
            return []
        try:
            lines = self.env['mobile.promotion.line'].sudo().search(
                [('promotion_id', '=', promo_id), ('state', '=', 'approved')],
                limit=limit * 3)
            out = []
            for l in lines:
                p = l.product_tmpl_id
                if not p or not p.active or not p.is_published:
                    continue
                pct = l.discount_pct or 0.0
                before = p.list_price or 0.0
                after = (l.price_applied or 0.0) or (before * (1.0 - pct / 100.0) if pct else before)
                out.append({
                    'name': p.name,
                    'img':  '/web/image/product.template/%d/image_256' % p.id,
                    'url':  p.website_url or ('/shop/%d' % p.id),
                    'before': before,
                    'after':  after,
                    'pct':    int(pct),
                })
                if len(out) >= limit:
                    break
            return out
        except Exception:
            return []

    def _ucp_freeship(self):
        """Live free-shipping threshold (per country), in this order:
        1) the freeship rules engine,
        2) the REAL delivery settings — this website's delivery carriers'
           free-over amount (own carriers first, else the global ones); the
           1000 sentinel = 'no free shipping',
        3) the manual fallback amount, else 0 (bar hidden)."""
        self.ensure_one()
        if not self.ucp_unlock_enabled:
            return 0.0
        # 1) freeship engine
        try:
            Rule = self.env.get('uellow.freeship.rule')
            if Rule is not None:
                amt = Rule.sudo().bar_threshold()
                if amt:
                    return float(amt)
        except Exception:
            pass
        # 2) delivery carriers (per country)
        try:
            Carrier = self.env['delivery.carrier'].sudo()
            for dom in ([('website_id', '=', self.id), ('active', '=', True)],
                        [('website_id', '=', False), ('active', '=', True)]):
                cs = Carrier.search(dom)
                amts = [c.amount for c in cs if c.amount and 0 < c.amount < 1000]
                if amts:
                    return float(min(amts))
                if cs:           # has its own carriers but none free-over → no bar
                    break
        except Exception:
            pass
        # 3) manual fallback
        return float(self.ucp_freeship_threshold or 0.0)
