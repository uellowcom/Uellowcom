"""Supplier scorecard — rate each vendor by real outcomes (idea #19).

Pure read-only analysis: for every vendor that supplies products, it measures
how many of their products actually sell, the average margin they leave us,
and how much of their stock goes dead — then rolls it into a 0-100 score so
you know, by numbers, who to keep buying from.
"""
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class SupplierScorecard(models.Model):
    _name = 'uellow.sc.supplier.scorecard'
    _description = 'Supplier Scorecard'
    _rec_name = 'vendor_id'
    _order = 'score desc'

    vendor_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade', index=True,
        string='Vendor')
    product_count = fields.Integer('Products Supplied', readonly=True)
    sold_count = fields.Integer('Products Sold', readonly=True)
    sold_ratio = fields.Float('Sell-through %', readonly=True)
    avg_margin_pct = fields.Float('Avg Margin %', readonly=True)
    dead_count = fields.Integer('Dead-stock Items', readonly=True)
    dead_ratio = fields.Float('Dead-stock %', readonly=True)
    score = fields.Integer('Score', readonly=True)
    grade = fields.Selection([
        ('a', 'A — Excellent'), ('b', 'B — Good'),
        ('c', 'C — Fair'), ('d', 'D — Poor'),
    ], readonly=True, string='Grade')
    last_scan = fields.Datetime('Last Scan', readonly=True)

    _sql_constraints = [
        ('uniq_vendor', 'unique(vendor_id)',
         'A scorecard already exists for this vendor.'),
    ]

    @api.model
    def cron_scan_suppliers(self):
        """Aggregate per-vendor performance from supplier info + sales + stock."""
        s = self.env['uellow.connector.settings'].get_settings()
        if not s.get('feat_scorecard'):
            return
        window = max(1, int(s.get('scorecard_window_days') or 180))
        today = fields.Date.today()
        since = today - timedelta(days=window)

        # 1) vendor → set(template ids) from purchase/supplier info
        seller = self.env['product.supplierinfo'].search(
            [('partner_id', '!=', False)])
        vendor_tmpls = {}
        all_tmpl_ids = set()
        for si in seller:
            tmpl = si.product_tmpl_id or (si.product_id.product_tmpl_id
                                          if si.product_id else False)
            if not tmpl:
                continue
            vendor_tmpls.setdefault(si.partner_id.id, set()).add(tmpl.id)
            all_tmpl_ids.add(tmpl.id)
        if not vendor_tmpls:
            return

        # 2) template → variant ids, and price/cost (bulk reads)
        tmpls = self.env['product.template'].browse(list(all_tmpl_ids))
        tmpl_price = {t.id: (t.list_price or 0.0, t.standard_price or 0.0)
                      for t in tmpls}
        variants = self.env['product.product'].search(
            [('product_tmpl_id', 'in', list(all_tmpl_ids))])
        variant_to_tmpl = {v.id: v.product_tmpl_id.id for v in variants}

        # 3) which variants sold in the window (one query) → sold template set
        sold_groups = self.env['stock.move'].read_group(
            domain=[('product_id', 'in', list(variant_to_tmpl.keys())),
                    ('location_dest_id.usage', '=', 'customer'),
                    ('state', '=', 'done'),
                    ('date', '>=', fields.Datetime.to_string(since))],
            fields=['product_id'], groupby=['product_id'])
        sold_tmpls = set()
        for r in sold_groups:
            if r.get('product_id'):
                t = variant_to_tmpl.get(r['product_id'][0])
                if t:
                    sold_tmpls.add(t)

        # 4) dead templates (active)
        dead_tmpls = set(self.env['uellow.dead.stock'].search(
            [('state', '=', 'active')]).mapped('product_tmpl_id.id'))

        now = fields.Datetime.now()
        existing = {r.vendor_id.id: r for r in self.search([])}
        to_create = []
        for vendor_id, tmpl_ids in vendor_tmpls.items():
            n = len(tmpl_ids)
            sold = len(tmpl_ids & sold_tmpls)
            dead = len(tmpl_ids & dead_tmpls)
            # average margin across this vendor's products
            margins = []
            for tid in tmpl_ids:
                price, cost = tmpl_price.get(tid, (0.0, 0.0))
                if price > 0 and cost > 0:
                    margins.append((price - cost) / price * 100.0)
            avg_margin = sum(margins) / len(margins) if margins else 0.0
            sold_ratio = (sold / n * 100.0) if n else 0.0
            dead_ratio = (dead / n * 100.0) if n else 0.0

            score = self._score(sold_ratio, avg_margin, dead_ratio)
            vals = {
                'product_count': n,
                'sold_count': sold,
                'sold_ratio': round(sold_ratio, 1),
                'avg_margin_pct': round(avg_margin, 1),
                'dead_count': dead,
                'dead_ratio': round(dead_ratio, 1),
                'score': score,
                'grade': self._grade(score),
                'last_scan': now,
            }
            row = existing.get(vendor_id)
            if row:
                row.write(vals)
            else:
                to_create.append(dict(vals, vendor_id=vendor_id))
        if to_create:
            self.create(to_create)
        self.env.cr.commit()

    @staticmethod
    def _score(sold_ratio, avg_margin, dead_ratio):
        """Composite 0-100: rewards sell-through & margin, penalises dead stock."""
        sell = min(sold_ratio, 100.0) * 0.5                 # up to 50 pts
        marg = min(avg_margin / 30.0, 1.0) * 30.0 if avg_margin > 0 else 0.0  # up to 30
        health = max(0.0, (100.0 - dead_ratio) / 100.0) * 20.0               # up to 20
        return int(round(max(0.0, min(100.0, sell + marg + health))))

    @staticmethod
    def _grade(score):
        if score >= 75:
            return 'a'
        if score >= 55:
            return 'b'
        if score >= 35:
            return 'c'
        return 'd'

    def action_view_products(self):
        """Open this vendor's supplied products."""
        self.ensure_one()
        tmpl_ids = self.env['product.supplierinfo'].search(
            [('partner_id', '=', self.vendor_id.id)]).mapped('product_tmpl_id.id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s — Products') % self.vendor_id.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', tmpl_ids)],
        }
