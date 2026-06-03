# -*- coding: utf-8 -*-
"""
Uellow Product Ranks — "Best Seller #N in <category>"
=====================================================
A daily job scores every product per public category from REAL signals
(sold quantity + revenue + rating, over a rolling window) and stores the
top-N as `uellow.product.rank` rows — globally AND per website (every
country app gets its own honest ladder, per the multi-website rule).

Surfaced through:
  • product cards   → gold badge for ranks ≤ badge_max_rank
  • product page    → full "#N Best Seller in <category>" strip
  • builder blocks  → the 'bestsellers' source now reads this table

Scoring (configurable weights):
  score = qty_sold·w_qty + revenue·w_revenue + rating_avg·ln(1+rating_count)·w_rating
"""
import logging
import math
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class UellowRankConfig(models.Model):
    _name = 'uellow.rank.config'
    _description = 'Product Rank Settings'

    name = fields.Char(default='Product Rank settings', required=True)
    enabled = fields.Boolean(default=True,
        help='Master switch — disables badges + builder integration.')
    window_days = fields.Integer('Sales window (days)', default=30,
        help='Ranks are computed over the last N days of confirmed sales.')
    top_n = fields.Integer('Ranks per category', default=10,
        help='Only the top N products per category get a rank row.')
    badge_max_rank = fields.Integer('Show badge up to rank', default=3,
        help='Product cards show the badge only for ranks ≤ this '
             '(the product page always shows all ranks).')
    min_qty = fields.Float('Minimum units sold to qualify', default=1.0)
    per_website = fields.Boolean('Per-website ladders', default=True,
        help='Also compute a separate ladder per website (country app). '
             'The API prefers the request website\'s ladder and falls '
             'back to the global one.')
    w_qty = fields.Float('Weight: units sold', default=1.0)
    w_revenue = fields.Float('Weight: revenue', default=0.2)
    w_rating = fields.Float('Weight: rating', default=2.0)
    last_compute = fields.Datetime(readonly=True)
    rank_count = fields.Integer(compute='_compute_rank_count')

    def _compute_rank_count(self):
        for r in self:
            r.rank_count = self.env['uellow.product.rank'].search_count([])

    @api.model
    def get_config(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    def action_recompute(self):
        self.env['uellow.product.rank'].recompute_ranks()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Product Ranks',
                       'message': 'Ranks recomputed successfully.',
                       'type': 'success'},
        }


class UellowProductRank(models.Model):
    _name = 'uellow.product.rank'
    _description = 'Product Rank in Category'
    _order = 'category_id, website_id, rank'
    _rec_name = 'display_label'

    product_tmpl_id = fields.Many2one('product.template', required=True,
                                      ondelete='cascade', index=True)
    category_id = fields.Many2one('product.public.category', required=True,
                                  ondelete='cascade', index=True)
    website_id = fields.Many2one('website', index=True,
        help='Empty = global ladder (all websites).')
    rank = fields.Integer(required=True, index=True)
    score = fields.Float(digits=(16, 4))
    qty_sold = fields.Float('Units sold (window)')
    revenue = fields.Float('Revenue (window)')
    window_days = fields.Integer()
    display_label = fields.Char(compute='_compute_display_label')

    @api.depends('rank', 'category_id', 'website_id')
    def _compute_display_label(self):
        for r in self:
            site = (' @%s' % r.website_id.name) if r.website_id else ''
            r.display_label = '#%s in %s%s' % (
                r.rank, r.category_id.name or '?', site)

    # ── computation ────────────────────────────────────────────────────
    @api.model
    def _sales_aggregates(self, date_from, website_id=None):
        """{product_tmpl_id: (qty, revenue)} from confirmed orders."""
        params = [date_from]
        site_clause = ''
        if website_id:
            site_clause = 'AND so.website_id = %s'
            params.append(website_id)
        self.env.cr.execute("""
            SELECT pp.product_tmpl_id, SUM(sol.product_uom_qty) AS qty,
                   SUM(sol.price_total) AS revenue
              FROM sale_order_line sol
              JOIN sale_order so ON so.id = sol.order_id
              JOIN product_product pp ON pp.id = sol.product_id
             WHERE so.state IN ('sale', 'done')
               AND so.date_order >= %s
               AND sol.product_uom_qty > 0
               AND sol.display_type IS NULL
               AND sol.price_total > 0
               """ + site_clause + """
             GROUP BY pp.product_tmpl_id
        """, params)
        return {r[0]: (float(r[1] or 0), float(r[2] or 0))
                for r in self.env.cr.fetchall()}

    @api.model
    def _build_ladder(self, aggregates, cfg, website_id=None):
        """Create rank rows for one ladder (global or per-website)."""
        if not aggregates:
            return 0
        Tmpl = self.env['product.template'].sudo()
        products = Tmpl.browse(list(aggregates.keys())).filtered(
            lambda p: p.active and p.is_published)
        # score every (product, category) pair
        per_cat = {}
        for p in products:
            qty, rev = aggregates.get(p.id, (0, 0))
            if qty < cfg.min_qty:
                continue
            rating_avg = float(getattr(p, 'rating_avg', 0) or 0)
            rating_count = int(getattr(p, 'rating_count', 0) or 0)
            score = (qty * cfg.w_qty + rev * cfg.w_revenue
                     + rating_avg * math.log1p(rating_count) * cfg.w_rating)
            for cat in p.public_categ_ids:
                per_cat.setdefault(cat.id, []).append(
                    (score, p.id, qty, rev))
        created = 0
        for cat_id, rows in per_cat.items():
            rows.sort(key=lambda t: -t[0])
            for idx, (score, pid, qty, rev) in enumerate(
                    rows[:max(1, cfg.top_n)], start=1):
                self.create({
                    'product_tmpl_id': pid,
                    'category_id': cat_id,
                    'website_id': website_id or False,
                    'rank': idx,
                    'score': round(score, 4),
                    'qty_sold': qty,
                    'revenue': rev,
                    'window_days': cfg.window_days,
                })
                created += 1
        return created

    @api.model
    def recompute_ranks(self):
        """Full rebuild — called by the daily cron and the Settings button."""
        cfg = self.env['uellow.rank.config'].sudo().get_config()
        if not cfg.enabled:
            return
        date_from = fields.Datetime.now() - timedelta(
            days=max(1, cfg.window_days))
        self.sudo().search([]).unlink()
        total = self._build_ladder(
            self._sales_aggregates(date_from), cfg, website_id=None)
        if cfg.per_website:
            sites = self.env['website'].sudo().search([])
            for w in sites:
                agg = self._sales_aggregates(date_from, website_id=w.id)
                if agg:
                    total += self._build_ladder(agg, cfg, website_id=w.id)
        cfg.last_compute = fields.Datetime.now()
        _logger.info('Product ranks recomputed: %s rows', total)
        return total

    # ── lookups (used by the mobile API + builder) ─────────────────────
    @api.model
    def best_for(self, product_tmpl_id, website_id=None):
        """The product's BEST (lowest) rank row — website ladder first."""
        dom = [('product_tmpl_id', '=', product_tmpl_id)]
        if website_id:
            rec = self.sudo().search(
                dom + [('website_id', '=', website_id)],
                order='rank asc', limit=1)
            if rec:
                return rec
        return self.sudo().search(
            dom + [('website_id', '=', False)], order='rank asc', limit=1)

    @api.model
    def all_for(self, product_tmpl_id, website_id=None):
        """Every category the product ranks in (deduped, best first)."""
        dom = [('product_tmpl_id', '=', product_tmpl_id)]
        recs = self.sudo().search(dom, order='rank asc')
        seen, out = set(), []
        # website-specific rows win over global rows of the same category
        for r in sorted(recs, key=lambda r: (r.rank, 0 if (
                website_id and r.website_id.id == website_id) else 1)):
            if website_id and r.website_id and r.website_id.id != website_id:
                continue
            if r.category_id.id in seen:
                continue
            seen.add(r.category_id.id)
            out.append(r)
        return out

    @api.model
    def top_products(self, category_id=None, website_id=None, limit=10):
        """Top ranked product templates (for builder blocks)."""
        dom = [('rank', '<=', max(1, limit))]
        dom.append(('website_id', '=', website_id or False))
        if category_id:
            dom.append(('category_id', '=', category_id))
        recs = self.sudo().search(dom, order='rank asc', limit=limit * 3)
        if not recs and website_id:
            return self.top_products(category_id=category_id,
                                     website_id=None, limit=limit)
        seen, ids = set(), []
        for r in recs:
            if r.product_tmpl_id.id not in seen:
                seen.add(r.product_tmpl_id.id)
                ids.append(r.product_tmpl_id.id)
            if len(ids) >= limit:
                break
        return self.env['product.template'].sudo().browse(ids)

    @api.autovacuum
    def _gc_stale(self):
        """Safety net: drop rows older than 3 windows (cron failed?)."""
        cfg = self.env['uellow.rank.config'].sudo().get_config()
        cutoff = fields.Datetime.now() - timedelta(
            days=max(3, cfg.window_days * 3))
        self.sudo().search([('create_date', '<', cutoff)]).unlink()
