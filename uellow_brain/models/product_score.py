"""Uellow Brain — Base Score precompute.

A stored, indexed `brain_score` on product.template, written by a nightly
cron (off the request path). Best Match then sorts via a plain indexed
ORDER BY → zero request-time cost. Score is COST/MARGIN-driven first.
"""
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplateBrain(models.Model):
    _inherit = 'product.template'

    brain_score = fields.Float('Brain score', default=0.0, index=True,
        copy=False,
        help='Precomputed Best-Match base score (0-100). Cron-written.')
    brain_score_at = fields.Datetime('Brain score at', copy=False)

    # ── cron ──────────────────────────────────────────────────────────
    @api.model
    def _cron_brain_recompute_scores(self):
        """Nightly: recompute brain_score for all published products.
        Cheap aggregate reads + one write per product. Safe no-op when the
        engine is disabled."""
        Cfg = self.env.get('uellow.brain.config')
        if Cfg is None:
            return
        cfg = Cfg.get_config()
        # We still compute even if disabled? Only if enabled, to save work.
        if not cfg.enabled:
            return
        self.sudo()._brain_compute_scores(cfg)

    @api.model
    def _brain_compute_scores_ui(self):
        """Called from the dashboard button — recompute now (forces even if
        engine disabled, so admins can preview)."""
        Cfg = self.env.get('uellow.brain.config')
        if Cfg is None:
            return 0
        return self.sudo()._brain_compute_scores(Cfg.get_config())

    @api.model
    def _brain_compute_scores(self, cfg, limit=None):
        Tmpl = self.sudo()
        prods = Tmpl.search([('is_published', '=', True),
                             ('sale_ok', '=', True)], limit=limit)
        if not prods:
            cfg.sudo().write({'last_scored': fields.Datetime.now(),
                              'scored_count': 0})
            return 0

        # ── one aggregate read for 30-day sold qty ──
        window = int(cfg.score_window_days or 30)
        since = datetime.utcnow() - timedelta(days=window)
        sold = {}
        try:
            self.env.cr.execute("""
                SELECT pp.product_tmpl_id, COALESCE(SUM(sol.product_uom_qty),0)
                FROM sale_order_line sol
                JOIN product_product pp ON pp.id = sol.product_id
                JOIN sale_order so ON so.id = sol.order_id
                WHERE so.date_order >= %s AND so.state IN ('sale','done')
                GROUP BY pp.product_tmpl_id
            """, (since,))
            sold = {r[0]: float(r[1] or 0) for r in self.env.cr.fetchall()}
        except Exception:
            sold = {}

        max_sold = max(sold.values()) if sold else 0.0
        now = fields.Datetime.now()
        # freshness reference
        newest = max((p.create_date for p in prods if p.create_date),
                     default=now)
        oldest = min((p.create_date for p in prods if p.create_date),
                     default=now)
        span = max((newest - oldest).days, 1)

        w = {
            'margin': (cfg.w_margin or 0) / 100.0,
            'sales': (cfg.w_sales or 0) / 100.0,
            'stock': (cfg.w_stock or 0) / 100.0,
            'rating': (cfg.w_rating or 0) / 100.0,
            'fresh': (cfg.w_fresh or 0) / 100.0,
        }
        wsum = sum(w.values()) or 1.0

        n = 0
        for p in prods:
            try:
                price = float(p.list_price or 0)
                cost = cfg._cost_of(p)
                margin = ((price - cost) / price) if (price > 0 and cost > 0) \
                    else (0.5 if price > 0 else 0.0)
                margin = max(0.0, min(1.0, margin))
                s_sales = (sold.get(p.id, 0.0) / max_sold) if max_sold else 0.0
                if getattr(p, 'is_storable', False):
                    s_stock = 1.0 if (p.qty_available or 0) > 0 else (
                        1.0 if getattr(p, 'allow_out_of_stock_order', True)
                        else 0.0)
                else:
                    s_stock = 1.0
                ra = float(getattr(p, 'rating_avg', 0) or 0)
                s_rating = max(0.0, min(1.0, ra / 5.0)) if ra else 0.4
                if p.create_date:
                    s_fresh = max(0.0, min(1.0,
                        1 - ((newest - p.create_date).days / span)))
                else:
                    s_fresh = 0.3

                raw = (w['margin'] * margin + w['sales'] * s_sales
                       + w['stock'] * s_stock + w['rating'] * s_rating
                       + w['fresh'] * s_fresh) / wsum
                score = round(raw * 100.0, 3)
                # penalties
                if getattr(p, 'is_storable', False) \
                        and (p.qty_available or 0) <= 0 \
                        and not getattr(p, 'allow_out_of_stock_order', True):
                    score *= 0.2
                if cfg.block_below_cost and cost > 0 and price < cost:
                    score *= 0.1
                if p.brain_score != score:
                    p.write({'brain_score': score, 'brain_score_at': now})
                n += 1
            except Exception:
                _logger.debug('brain score failed for %s', p.id, exc_info=True)
            # commit in batches to keep memory/locks small
            if n % 500 == 0:
                self.env.cr.commit()
        cfg.sudo().write({'last_scored': now, 'scored_count': n})
        _logger.info('Uellow Brain: scored %s products', n)
        return n
