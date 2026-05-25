from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class KPISnapshot(models.Model):
    """Hourly KPI snapshot for the CEO dashboard."""
    _name = 'uellow.kpi.snapshot'
    _description = 'KPI Snapshot'
    _order = 'snapshot_at desc'

    snapshot_at = fields.Datetime('Snapshot Time', default=fields.Datetime.now, index=True)
    period = fields.Selection([
        ('today',   'Today'),
        ('week',    'This Week'),
        ('month',   'This Month'),
        ('quarter', 'This Quarter'),
    ], default='today')

    # Revenue
    gmv = fields.Float('GMV (Gross Merchandise Value)')
    net_revenue = fields.Float('Net Revenue (after refunds)')
    commission_earned = fields.Float('Commission Earned')
    take_rate = fields.Float('Take Rate (%)')

    # Orders
    order_count = fields.Integer('Total Orders')
    avg_order_value = fields.Float('Avg Order Value')
    cod_count = fields.Integer('COD Orders')
    online_count = fields.Integer('Online Payment Orders')
    cancelled_count = fields.Integer('Cancelled Orders')
    cancel_rate = fields.Float('Cancellation Rate (%)')

    # Vendors
    vendor_count_active = fields.Integer('Active Vendors')
    vendor_count_new = fields.Integer('New Vendors (period)')
    vendor_count_total = fields.Integer('Total Vendors')

    # Customers
    customer_count_new = fields.Integer('New Customers')
    customer_count_returning = fields.Integer('Returning Customers')
    avg_ltv = fields.Float('Avg Customer LTV')

    # Website
    conversion_rate = fields.Float('Conversion Rate (%)')
    cart_abandon_rate = fields.Float('Cart Abandon Rate (%)')

    # Loyalty
    points_issued = fields.Integer('Loyalty Points Issued')
    points_redeemed = fields.Integer('Loyalty Points Redeemed')

    @api.model
    def cron_take_snapshot(self):
        """Hourly: compute and store KPI snapshot."""
        now = fields.Datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        for period, start in [('today', today_start), ('week', week_start), ('month', month_start)]:
            self._compute_snapshot(period, start, now)

    def _compute_snapshot(self, period, start, end):
        SaleOrder = self.env['sale.order']
        orders = SaleOrder.search([
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', start),
            ('date_order', '<=', end),
        ])
        cancelled = SaleOrder.search_count([
            ('state', '=', 'cancel'),
            ('date_order', '>=', start),
        ])
        total_orders = len(orders)
        gmv = sum(orders.mapped('amount_total'))
        avg_ov = gmv / total_orders if total_orders else 0
        cancel_rate = cancelled / (total_orders + cancelled) * 100 if (total_orders + cancelled) else 0

        # Take rate from commissions
        commission = 0.0
        take_rate = 0.0
        if 'uellow.vendor.commission' in self.env:
            commissions = self.env['uellow.vendor.commission'].search([
                ('order_date', '>=', start),
                ('order_date', '<=', end),
            ])
            commission = sum(commissions.mapped('commission_amount'))
            take_rate = commission / gmv * 100 if gmv else 0

        # Vendors
        vendor_count = 0
        vendor_new = 0
        if 'uellow.vendor' in self.env:
            vendor_count = self.env['uellow.vendor'].search_count([('state', '=', 'active')])
            vendor_new = self.env['uellow.vendor'].search_count([
                ('state', '=', 'active'),
                ('approval_date', '>=', start),
            ])

        # Customers
        customer_ids = orders.mapped('partner_id').ids
        new_customers = 0
        for partner_id in customer_ids:
            first_order = SaleOrder.search([
                ('partner_id', '=', partner_id),
                ('state', 'in', ('sale', 'done')),
            ], order='date_order asc', limit=1)
            if first_order and first_order.date_order >= start:
                new_customers += 1

        self.create({
            'snapshot_at': fields.Datetime.now(),
            'period': period,
            'gmv': gmv,
            'commission_earned': commission,
            'take_rate': take_rate,
            'order_count': total_orders,
            'avg_order_value': avg_ov,
            'cancelled_count': cancelled,
            'cancel_rate': cancel_rate,
            'vendor_count_active': vendor_count,
            'vendor_count_new': vendor_new,
            'customer_count_new': new_customers,
            'customer_count_returning': len(customer_ids) - new_customers,
        })
