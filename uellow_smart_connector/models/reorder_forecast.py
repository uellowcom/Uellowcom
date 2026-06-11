"""Reorder forecast — predicts run-out of fast-selling products (idea #25).

The inverse of dead-stock: instead of finding what never moves, it finds the
winners that are about to run dry, so we restock BEFORE losing sales.
"""
import logging
import math
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

_BATCH = 200   # commit interval


class ReorderForecast(models.Model):
    _name = 'uellow.sc.reorder.forecast'
    _description = 'Reorder Forecast'
    _rec_name = 'product_id'
    _order = 'days_to_runout asc'

    product_id = fields.Many2one(
        'product.product', required=True, ondelete='cascade', index=True,
        string='Product (Variant)')
    product_tmpl_id = fields.Many2one(
        'product.template', compute='_compute_tmpl', store=True, string='Product')

    qty_on_hand = fields.Float('Qty On Hand', readonly=True)
    units_sold = fields.Float('Units Sold (window)', readonly=True)
    avg_daily_sales = fields.Float('Avg / Day', readonly=True, digits=(12, 3))
    days_to_runout = fields.Integer('Days to Run-out', readonly=True)
    runout_date = fields.Date('Projected Run-out', readonly=True)
    suggested_qty = fields.Integer('Suggested Reorder Qty', readonly=True)
    projected_demand_30d = fields.Integer(
        '30-Day Demand', readonly=True,
        help='Projected units that will sell in the next 30 days at the current rate.')

    state = fields.Selection([
        ('urgent',   'Urgent — restock now'),
        ('reorder',  'Reorder soon'),
        ('ok',       'Healthy'),
        ('resolved', 'Handled'),
        ('ignored',  'Ignored'),
    ], default='ok', string='Status', index=True)

    _sql_constraints = [
        ('uniq_product', 'unique(product_id)',
         'A reorder forecast already exists for this product.'),
    ]

    @api.depends('product_id')
    def _compute_tmpl(self):
        for rec in self:
            rec.product_tmpl_id = rec.product_id.product_tmpl_id or False

    @api.model
    def cron_scan_reorder(self):
        """Measure each in-stock product's sales velocity and project run-out."""
        s = self.env['uellow.connector.settings'].get_settings()
        if not s.get('feat_reorder'):
            return
        velocity_days = max(1, int(s.get('reorder_velocity_days') or 60))
        lead_days = max(1, int(s.get('reorder_lead_days') or 14))
        safety_days = max(0, int(s.get('reorder_safety_days') or 7))
        today = fields.Date.today()
        since = today - timedelta(days=velocity_days)

        # qty on hand per product (one query)
        quant_groups = self.env['stock.quant'].read_group(
            domain=[('location_id.usage', '=', 'internal'), ('quantity', '>', 0)],
            fields=['product_id', 'quantity:sum'], groupby=['product_id'])
        qty_by_product = {r['product_id'][0]: (r['quantity'] or 0)
                          for r in quant_groups if r.get('product_id')}
        if not qty_by_product:
            return

        # units sold in the window per product (one query, customer-bound moves)
        sold_groups = self.env['stock.move'].read_group(
            domain=[('product_id', 'in', list(qty_by_product.keys())),
                    ('location_dest_id.usage', '=', 'customer'),
                    ('state', '=', 'done'),
                    ('date', '>=', fields.Datetime.to_string(since))],
            fields=['product_id', 'product_qty:sum'], groupby=['product_id'])
        sold_by_product = {r['product_id'][0]: (r['product_qty'] or 0)
                           for r in sold_groups if r.get('product_id')}

        product_ids = list(qty_by_product.keys())
        for i in range(0, len(product_ids), _BATCH):
            chunk = product_ids[i:i + _BATCH]
            self._process_reorder_chunk(
                chunk, qty_by_product, sold_by_product,
                velocity_days, lead_days, safety_days, today)
            self.env.cr.commit()
            _logger.info('Smart Connector reorder cron: %d/%d scanned',
                         min(i + _BATCH, len(product_ids)), len(product_ids))

    def _process_reorder_chunk(self, product_ids, qty_map, sold_map,
                               velocity_days, lead_days, safety_days, today):
        existing = {r.product_id.id: r
                    for r in self.search([('product_id', 'in', product_ids)])}
        to_create = []
        for pid in product_ids:
            qty = qty_map.get(pid, 0)
            sold = sold_map.get(pid, 0)
            avg_daily = sold / velocity_days if velocity_days else 0.0
            row = existing.get(pid)

            # No sales velocity → not a reorder concern (that's dead-stock's job)
            if avg_daily <= 0:
                if row and row.state not in ('ignored',):
                    row.write({'state': 'ok', 'avg_daily_sales': 0.0,
                               'days_to_runout': 0, 'suggested_qty': 0,
                               'qty_on_hand': qty, 'units_sold': sold,
                               'runout_date': False})
                continue

            days_left = int(qty / avg_daily) if avg_daily > 0 else 9999
            runout = today + timedelta(days=min(days_left, 3650))
            # target cover = lead time + safety stock; suggest the shortfall
            target_units = avg_daily * (lead_days + safety_days)
            suggested = max(0, math.ceil(target_units - qty))

            if days_left <= lead_days:
                state = 'urgent'
            elif days_left <= lead_days + safety_days:
                state = 'reorder'
            else:
                state = 'ok'

            vals = {
                'qty_on_hand': qty,
                'units_sold': sold,
                'avg_daily_sales': round(avg_daily, 3),
                'days_to_runout': days_left,
                'runout_date': runout,
                'suggested_qty': suggested,
                'projected_demand_30d': int(math.ceil(avg_daily * 30)),
            }
            if row:
                # don't override a manual ignore/resolve unless it's urgent again
                if row.state in ('ignored', 'resolved') and state != 'urgent':
                    vals.pop('suggested_qty', None)
                else:
                    vals['state'] = state
                row.write(vals)
            else:
                to_create.append(dict(vals, product_id=pid, state=state))
        if to_create:
            self.create(to_create)

    def action_resolve(self):
        for r in self:
            r.state = 'resolved'

    def action_ignore(self):
        for r in self:
            r.state = 'ignored'
