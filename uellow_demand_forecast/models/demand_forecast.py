from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class DemandForecast(models.Model):
    _name = 'uellow.demand.forecast'
    _description = 'AI Demand Forecast'
    _rec_name = 'product_id'
    _order = 'forecast_date desc'

    product_id = fields.Many2one('product.product', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', store=True)
    vendor_partner_id = fields.Many2one('res.partner', string='Vendor')

    forecast_date = fields.Date('Forecast Date', required=True)
    forecast_units = fields.Integer('Forecasted Units Needed')
    current_stock = fields.Float('Current Stock', readonly=True)
    reorder_needed = fields.Boolean('Reorder Needed', compute='_compute_reorder', store=True)
    reorder_qty = fields.Integer('Suggested Reorder Qty', compute='_compute_reorder', store=True)

    confidence = fields.Float('Confidence (%)', default=75.0)
    trend = fields.Selection([
        ('up',     'Trending Up'),
        ('stable', 'Stable'),
        ('down',   'Trending Down'),
    ], default='stable')
    seasonality = fields.Char('Seasonality Notes')

    avg_daily_sales = fields.Float('Avg Daily Sales (last 30d)', readonly=True)
    peak_factor = fields.Float('Peak Factor', default=1.0,
                               help='Multiplier for seasonal peaks (Ramadan, National Day, etc.)')
    lead_time_days = fields.Integer('Lead Time (days)', default=3)

    state = fields.Selection([
        ('active',    'Active'),
        ('resolved',  'Resolved'),
        ('ignored',   'Ignored'),
    ], default='active')

    @api.depends('forecast_units', 'current_stock', 'lead_time_days', 'avg_daily_sales')
    def _compute_reorder(self):
        for rec in self:
            safety_stock = rec.avg_daily_sales * rec.lead_time_days
            if rec.current_stock < (rec.forecast_units + safety_stock):
                rec.reorder_needed = True
                rec.reorder_qty = max(0, int(
                    rec.forecast_units + safety_stock - rec.current_stock))
            else:
                rec.reorder_needed = False
                rec.reorder_qty = 0

    @api.model
    def cron_run_forecast(self):
        """Weekly: compute demand forecasts for all active products."""
        today = fields.Date.today()
        next_week = today + timedelta(days=7)

        products = self.env['product.product'].search([
            ('type', '=', 'product'),
            ('active', '=', True),
        ])
        for product in products:
            self._forecast_product(product, next_week)

    def _forecast_product(self, product, forecast_date):
        """Simple moving average forecast."""
        cutoff_30 = fields.Datetime.now() - timedelta(days=30)
        cutoff_90 = fields.Datetime.now() - timedelta(days=90)

        moves_30 = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('location_dest_id.usage', '=', 'customer'),
            ('state', '=', 'done'),
            ('date', '>=', cutoff_30),
        ])
        moves_90 = self.env['stock.move'].search([
            ('product_id', '=', product.id),
            ('location_dest_id.usage', '=', 'customer'),
            ('state', '=', 'done'),
            ('date', '>=', cutoff_90),
        ])

        qty_30 = sum(m.product_qty for m in moves_30)
        qty_90 = sum(m.product_qty for m in moves_90)
        avg_daily_30 = qty_30 / 30
        avg_daily_90 = qty_90 / 90 if qty_90 > 0 else 0

        # Trend detection
        if avg_daily_30 > avg_daily_90 * 1.2:
            trend = 'up'
        elif avg_daily_30 < avg_daily_90 * 0.8:
            trend = 'down'
        else:
            trend = 'stable'

        forecast_units = int(avg_daily_30 * 7)  # 7-day forecast

        # Get current stock
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id.usage', '=', 'internal'),
        ])
        current_stock = sum(q.quantity for q in quants)

        # Update or create forecast
        existing = self.search([
            ('product_id', '=', product.id),
            ('forecast_date', '=', forecast_date),
            ('state', '=', 'active'),
        ], limit=1)

        vals = {
            'product_id': product.id,
            'forecast_date': forecast_date,
            'forecast_units': forecast_units,
            'current_stock': current_stock,
            'avg_daily_sales': avg_daily_30,
            'trend': trend,
        }
        if existing:
            existing.write(vals)
        elif forecast_units > 0:
            self.create(vals)

    def action_ignore(self):
        self.state = 'ignored'

    def action_resolve(self):
        self.state = 'resolved'
