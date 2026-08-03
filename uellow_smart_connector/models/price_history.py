# -*- coding: utf-8 -*-
"""
Internal Price Intelligence — v2 (price history + trend indicators)
===================================================================
The competitor checker watches OTHER stores; this watches OUR prices
from inside Odoo. Every `list_price` / `compare_list_price` write on a
product is captured as a `uellow.price.history` row (plus a daily
snapshot cron as a safety net for changes that slip past the ORM hook).

From the history we derive customer-facing indicators:
  • trend (up / down / stable) + % change over the window
  • "lowest price in 90 days" flag — the strongest conversion signal
  • volatility (number of changes in the window)
  • sparkline points for the app's mini chart

Surfaced on product cards, the product page and a builder block
('price_drops' source = biggest recent drops).
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# v2.1 — single source of truth for the up/down/stable threshold (was 0.01%
# at capture time but 0.05% in the indicator, so the same change could read
# 'down' on the card yet 'stable' in history).
_TREND_EPS_PCT = 0.05


class UellowPriceHistory(models.Model):
    _name = 'uellow.price.history'
    _description = 'Price Change History'
    _order = 'recorded_at desc'
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one('product.template', required=True,
                                      ondelete='cascade', index=True,
                                      string='Product')
    price = fields.Float('Price', required=True, digits=(16, 3))
    compare_price = fields.Float('Compare Price', digits=(16, 3))
    prev_price = fields.Float('Previous Price', digits=(16, 3))
    change_pct = fields.Float('Change %', digits=(8, 2))
    direction = fields.Selection([
        ('up', '▲ Increased'),
        ('down', '▼ Decreased'),
        ('stable', '— Stable'),
    ], default='stable', index=True, string='Direction')
    source = fields.Selection([
        ('write', 'Direct edit'),
        ('snapshot', 'Daily snapshot'),
        ('baseline', 'Baseline'),
    ], default='write', string='Source')
    recorded_at = fields.Datetime('Recorded At', required=True, index=True,
                                  default=fields.Datetime.now)

    # ── capture ────────────────────────────────────────────────────────
    @api.model
    def log_change(self, product, source='write'):
        """Record the product's current price if it differs from the last row."""
        try:
            last = self.sudo().search(
                [('product_tmpl_id', '=', product.id)],
                order='recorded_at desc', limit=1)
            price = float(product.list_price or 0)
            if last and abs(last.price - price) < 0.0005:
                return self.browse()
            prev = last.price if last else price
            change = ((price - prev) / prev * 100.0) if prev else 0.0
            direction = ('up' if change > _TREND_EPS_PCT else
                         'down' if change < -_TREND_EPS_PCT else 'stable')
            return self.sudo().create({
                'product_tmpl_id': product.id,
                'price': price,
                'compare_price': float(product.compare_list_price or 0),
                'prev_price': prev,
                'change_pct': round(change, 2),
                'direction': direction if last else 'stable',
                'source': source if last else 'baseline',
            })
        except Exception:
            _logger.exception('price history log failed for %s', product.id)
            return self.browse()

    @api.model
    def cron_daily_snapshot(self):
        """Safety net + seeds baselines for new products. Only writes rows
        when the price actually changed, so the table stays lean."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow.sc.internal_price_watch', '1') in (
                '0', 'False', 'false'):
            return
        Tmpl = self.env['product.template'].sudo()
        for p in Tmpl.search([('is_published', '=', True),
                              ('active', '=', True),
                              ('is_dropship', '=', False)]):  # skip World products
            self.log_change(p, source='snapshot')

    # ── indicators (mobile API + builder) ──────────────────────────────
    @api.model
    def trend_for(self, product_tmpl_id, window_days=30, lowest_days=90):
        """Compact card indicator dict or None when nothing interesting."""
        now = fields.Datetime.now()
        rows = self.sudo().search(
            [('product_tmpl_id', '=', product_tmpl_id),
             ('recorded_at', '>=', now - timedelta(days=lowest_days))],
            order='recorded_at asc')
        if len(rows) < 2:
            return None
        current = rows[-1].price
        win_rows = [r for r in rows
                    if r.recorded_at >= now - timedelta(days=window_days)]
        # v2.1.28 — the indicator follows the LAST actual change (current
        # vs previous price point). Comparing to the window start hid the
        # arrow for any price that round-tripped back to its old value.
        prev = rows[-2].price
        change = ((current - prev) / prev * 100.0) if prev else 0.0
        prices = [r.price for r in rows]
        is_lowest = current <= min(prices) + 0.0005 and max(prices) > current
        direction = ('down' if change < -_TREND_EPS_PCT else
                     'up' if change > _TREND_EPS_PCT else 'stable')
        # v2.1.28 — stable is a signal too (shown with its own icon).
        return {
            'direction': direction,
            'change_pct': round(abs(change), 1),
            'is_lowest': bool(is_lowest),
            'lowest_days': lowest_days,
            'changes': max(0, len(win_rows) - 1),
        }

    @api.model
    def history_for(self, product_tmpl_id, days=90, max_points=30):
        """Sparkline payload for the product page."""
        now = fields.Datetime.now()
        rows = self.sudo().search(
            [('product_tmpl_id', '=', product_tmpl_id),
             ('recorded_at', '>=', now - timedelta(days=days))],
            order='recorded_at asc')
        if not rows:
            return None
        pts = [{'t': r.recorded_at.strftime('%Y-%m-%d'), 'p': r.price}
               for r in rows]
        if len(pts) > max_points:
            step = len(pts) / float(max_points)
            pts = [pts[int(i * step)] for i in range(max_points - 1)] + [pts[-1]]
        prices = [r.price for r in rows]
        return {
            'points': pts,
            'min': min(prices),
            'max': max(prices),
            'current': prices[-1],
            'days': days,
            'changes': max(0, len(rows) - 1),
        }

    @api.model
    def top_drops(self, days=14, limit=10):
        """Templates with the biggest price DROPS recently (builder block)."""
        now = fields.Datetime.now()
        self.env.cr.execute("""
            SELECT product_tmpl_id, MIN(change_pct) AS drop
              FROM uellow_price_history
             WHERE recorded_at >= %s AND direction = 'down'
             GROUP BY product_tmpl_id
             ORDER BY drop ASC
             LIMIT %s
        """, [now - timedelta(days=days), limit * 2])
        ids = [r[0] for r in self.env.cr.fetchall()]
        recs = self.env['product.template'].sudo().browse(ids).filtered(
            lambda p: p.active and p.is_published)
        return recs[:limit]


class ProductTemplatePriceWatch(models.Model):
    """ORM hook: every price write becomes a history row instantly."""
    _inherit = 'product.template'

    def write(self, vals):
        watch = ('list_price' in vals or 'compare_list_price' in vals)
        res = super().write(vals)
        if watch:
            try:
                ICP = self.env['ir.config_parameter'].sudo()
                if ICP.get_param('uellow.sc.internal_price_watch', '1') not in (
                        '0', 'False', 'false'):
                    Hist = self.env['uellow.price.history']
                    for p in self:
                        Hist.log_change(p, source='write')
            except Exception:
                _logger.exception('price watch hook failed')
        return res
