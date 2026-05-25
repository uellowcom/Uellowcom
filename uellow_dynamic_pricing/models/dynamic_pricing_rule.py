from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class DynamicPricingRule(models.Model):
    _name = 'uellow.dynamic.pricing.rule'
    _description = 'Dynamic Pricing Rule'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    rule_type = fields.Selection([
        ('peak_hours',    'Peak Hours Boost'),
        ('dead_stock',    'Dead Stock Discount'),
        ('demand_surge',  'Demand Surge'),
        ('off_peak',      'Off-Peak Discount'),
        ('competitor',    'Beat Competitor Price'),
    ], required=True, default='off_peak')

    # Targeting
    apply_to = fields.Selection([
        ('all',      'All Products'),
        ('category', 'Specific Category'),
        ('vendor',   'Specific Vendor'),
        ('manual',   'Manual Product List'),
    ], default='all')
    category_id = fields.Many2one('product.category')
    product_ids = fields.Many2many('product.template', string='Products')

    # Adjustment
    adjustment_type = fields.Selection([
        ('pct_increase', 'Percentage Increase'),
        ('pct_decrease', 'Percentage Decrease'),
        ('fixed_amount', 'Fixed Amount'),
    ], default='pct_decrease')
    adjustment_value = fields.Float('Adjustment Value', required=True)

    # Peak hours
    peak_start_hour = fields.Integer('Peak Start Hour (0-23)', default=18)
    peak_end_hour = fields.Integer('Peak End Hour (0-23)', default=22)
    peak_days = fields.Char('Peak Days (0=Mon,6=Sun)', default='0,1,2,3,4,5,6')

    # Dead stock
    dead_stock_days = fields.Integer('No Sales for (days)', default=30)

    # Limits
    max_discount_pct = fields.Float('Max Discount (%)', default=30.0)
    min_price = fields.Float('Minimum Price (KD)', default=0.5)
    max_price_increase_pct = fields.Float('Max Price Increase (%)', default=20.0)

    times_applied = fields.Integer('Times Applied', default=0, readonly=True)
    last_applied = fields.Datetime('Last Applied', readonly=True)

    def _is_peak_now(self):
        now = datetime.now()
        try:
            peak_days = [int(d) for d in self.peak_days.split(',')]
        except Exception:
            peak_days = list(range(7))
        return (now.weekday() in peak_days and
                self.peak_start_hour <= now.hour < self.peak_end_hour)

    @api.model
    def cron_apply_pricing(self):
        rules = self.search([('active', '=', True)])
        for rule in rules:
            try:
                rule._apply_rule()
            except Exception as e:
                _logger.error('Dynamic pricing rule %s failed: %s', rule.name, e)

    def _apply_rule(self):
        products = self._get_target_products()
        if not products:
            return

        now = datetime.now()
        for product in products:
            base_price = product.list_price
            if base_price <= 0:
                continue
            new_price = base_price
            apply = False

            if self.rule_type == 'peak_hours' and self._is_peak_now():
                pct = min(self.adjustment_value, self.max_price_increase_pct)
                new_price = base_price * (1 + pct / 100)
                apply = True
            elif self.rule_type in ('dead_stock', 'off_peak'):
                pct = min(self.adjustment_value, self.max_discount_pct)
                new_price = base_price * (1 - pct / 100)
                apply = True
            elif self.rule_type == 'demand_surge':
                # Check recent order volume
                from datetime import timedelta
                cutoff = fields.Datetime.now() - timedelta(hours=24)
                recent_orders = self.env['sale.order.line'].search_count([
                    ('product_id.product_tmpl_id', '=', product.id),
                    ('order_id.date_order', '>=', cutoff),
                    ('order_id.state', 'in', ('sale', 'done')),
                ])
                if recent_orders >= 5:  # 5+ orders in 24h = demand surge
                    pct = min(self.adjustment_value, self.max_price_increase_pct)
                    new_price = base_price * (1 + pct / 100)
                    apply = True

            if apply:
                new_price = max(new_price, self.min_price)
                new_price = round(new_price, 3)
                product.write({'dynamic_price': new_price, 'dynamic_rule_id': self.id})

        self.write({
            'times_applied': self.times_applied + 1,
            'last_applied': fields.Datetime.now(),
        })

    def _get_target_products(self):
        domain = [('website_published', '=', True)]
        if self.apply_to == 'category' and self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        elif self.apply_to == 'manual':
            return self.product_ids
        return self.env['product.template'].search(domain, limit=200)
