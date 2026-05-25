from odoo import models, fields, api, _
from datetime import timedelta


class CustomerLTV(models.Model):
    _name = 'uellow.customer.ltv'
    _description = 'Customer Lifetime Value'
    _rec_name = 'partner_id'
    _order = 'ltv_score desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)

    # Core metrics
    total_revenue = fields.Float('Total Revenue', readonly=True)
    order_count = fields.Integer('Order Count', readonly=True)
    avg_order_value = fields.Float('Avg Order Value', readonly=True)
    first_order_date = fields.Date('First Order', readonly=True)
    last_order_date = fields.Date('Last Order', readonly=True)
    days_since_last_order = fields.Integer('Days Since Last Order', readonly=True)
    order_frequency_days = fields.Float('Avg Days Between Orders', readonly=True)

    # LTV Score (0-100)
    ltv_score = fields.Float('LTV Score', readonly=True)

    # Segment
    segment = fields.Selection([
        ('vip',        'VIP'),
        ('active',     'Active'),
        ('at_risk',    'At Risk'),
        ('dormant',    'Dormant'),
        ('lost',       'Lost'),
        ('new',        'New'),
    ], default='new', string='Segment', index=True)

    # Churn risk
    churn_probability = fields.Float('Churn Probability (%)', readonly=True)

    # Currency
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
    )

    last_computed = fields.Datetime('Last Computed', readonly=True)

    _sql_constraints = [
        ('unique_partner', 'UNIQUE(partner_id)', 'Partner already has an LTV record.'),
    ]

    @api.model
    def cron_compute_all(self):
        """Daily: recompute LTV for all customers with orders."""
        partners = self.env['sale.order'].search([
            ('state', 'in', ('sale', 'done')),
        ]).mapped('partner_id')
        for partner in partners:
            self._compute_for_partner(partner)

    @api.model
    def _compute_for_partner(self, partner):
        orders = self.env['sale.order'].search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ('sale', 'done')),
        ])
        if not orders:
            return

        total_revenue = sum(orders.mapped('amount_total'))
        order_count = len(orders)
        avg_order_value = total_revenue / order_count if order_count else 0

        dates = sorted(orders.mapped('date_order'))
        first_date = dates[0].date()
        last_date = dates[-1].date()
        days_since = (fields.Date.today() - last_date).days

        # Frequency
        if len(dates) > 1:
            total_days = (dates[-1] - dates[0]).days
            frequency = total_days / (len(dates) - 1)
        else:
            frequency = 0

        # LTV Score (simplified RFM)
        recency_score = max(0, 100 - days_since * 0.5)
        freq_score = min(100, order_count * 10)
        monetary_score = min(100, avg_order_value / 10)
        ltv_score = (recency_score * 0.3 + freq_score * 0.3 + monetary_score * 0.4)

        # Segment
        if ltv_score >= 80:
            segment = 'vip'
        elif ltv_score >= 60 and days_since <= 30:
            segment = 'active'
        elif days_since <= 60:
            segment = 'at_risk'
        elif days_since <= 180:
            segment = 'dormant'
        elif days_since > 180:
            segment = 'lost'
        else:
            segment = 'new'

        churn_prob = min(100, days_since * 0.3 + (100 - ltv_score) * 0.5)

        existing = self.search([('partner_id', '=', partner.id)], limit=1)
        vals = {
            'partner_id': partner.id,
            'total_revenue': total_revenue,
            'order_count': order_count,
            'avg_order_value': avg_order_value,
            'first_order_date': first_date,
            'last_order_date': last_date,
            'days_since_last_order': days_since,
            'order_frequency_days': frequency,
            'ltv_score': ltv_score,
            'segment': segment,
            'churn_probability': churn_prob,
            'last_computed': fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
        else:
            self.create(vals)
