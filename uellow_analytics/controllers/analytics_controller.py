import json
import logging
import datetime

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class AnalyticsController(http.Controller):

    def _json(self, data):
        return Response(
            json.dumps(data, ensure_ascii=False, default=str),
            mimetype='application/json',
        )

    def _date_range(self, period='month'):
        now   = datetime.datetime.now()
        today = now.date()
        if period == 'today':
            start = datetime.datetime.combine(today, datetime.time.min)
        elif period == 'week':
            start = datetime.datetime.combine(today - datetime.timedelta(days=7), datetime.time.min)
        elif period == 'month':
            start = datetime.datetime.combine(today - datetime.timedelta(days=30), datetime.time.min)
        elif period == 'quarter':
            start = datetime.datetime.combine(today - datetime.timedelta(days=90), datetime.time.min)
        else:
            start = datetime.datetime.combine(today - datetime.timedelta(days=30), datetime.time.min)
        return start, now

    # ── Main Dashboard Data ───────────────────────────────────────────────────

    @http.route('/analytics/dashboard', type='json', auth='user', methods=['POST', 'GET'], csrf=False)
    def get_dashboard(self, **kwargs):
        # Handle both direct params and nested params
        period = kwargs.get('period', 'month')
        if not period:
            period = 'month'
        start, end = self._date_range(period)
        env = request.env

        # ── AI Chat Stats ──────────────────────────────────────────────────
        sessions = env['ai.chat.session'].sudo().search([
            ('write_date', '>=', start),
            ('write_date', '<=', end),
        ])

        total_sessions  = len(sessions)
        happy_sessions  = len(sessions.filtered(lambda s: s.last_state in ('happy', 'excited')))
        sad_sessions    = len(sessions.filtered(lambda s: s.last_state == 'sad'))

        # Sessions per day (last 7 days)
        sessions_by_day = {}
        for i in range(7):
            day = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            sessions_by_day[day] = 0
        for s in sessions:
            day = str(s.write_date)[:10]
            if day in sessions_by_day:
                sessions_by_day[day] += 1
        sessions_chart = [
            {'date': k, 'count': v}
            for k, v in sorted(sessions_by_day.items())
        ]

        # ── Sales Stats ────────────────────────────────────────────────────
        orders = env['sale.order'].sudo().search([
            ('date_order', '>=', start),
            ('date_order', '<=', end),
            ('state', 'in', ['sale', 'done']),
        ])

        total_revenue   = sum(o.amount_total for o in orders)
        total_orders    = len(orders)
        avg_order_value = round(total_revenue / total_orders, 3) if total_orders else 0

        # Revenue per day (last 7 days)
        revenue_by_day = {}
        for i in range(7):
            day = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
            revenue_by_day[day] = 0.0
        for o in orders:
            day = str(o.date_order)[:10]
            if day in revenue_by_day:
                revenue_by_day[day] += o.amount_total
        revenue_chart = [
            {'date': k, 'amount': round(v, 3)}
            for k, v in sorted(revenue_by_day.items())
        ]

        # ── Conversion Rate ────────────────────────────────────────────────
        # Orders that came through AI sessions
        ai_conversion = round(
            (happy_sessions / total_sessions * 100) if total_sessions else 0, 1
        )

        # ── Top Products ───────────────────────────────────────────────────
        top_products_data = {}
        for order in orders:
            for line in order.order_line:
                pid  = line.product_id.id
                name = line.product_id.name
                if pid not in top_products_data:
                    top_products_data[pid] = {'name': name, 'count': 0, 'revenue': 0}
                top_products_data[pid]['count']   += line.product_uom_qty
                top_products_data[pid]['revenue'] += line.price_subtotal

        top_products = sorted(
            top_products_data.values(),
            key=lambda x: x['revenue'], reverse=True
        )[:10]

        # ── Reviewer Stats ─────────────────────────────────────────────────
        reviewer_stats = {'total': 0, 'completed': 0, 'conversion': 0}
        ReviewRequest = env.get('review.request')
        if ReviewRequest:
            rv_requests = ReviewRequest.sudo().search([
                ('create_date', '>=', start),
                ('create_date', '<=', end),
            ])
            completed = rv_requests.filtered(lambda r: r.state == 'completed')
            reviewer_stats = {
                'total':      len(rv_requests),
                'completed':  len(completed),
                'conversion': round(len(completed) / len(rv_requests) * 100, 1) if rv_requests else 0,
                'recommend':  len(completed.filtered(lambda r: r.reviewer_verdict == 'recommend')),
            }

        # ── Loyalty Stats ──────────────────────────────────────────────────
        loyalty_stats = {'total_accounts': 0, 'points_issued': 0}
        LoyaltyAccount = env.get('loyalty.account')
        if LoyaltyAccount:
            accounts = LoyaltyAccount.sudo().search([])
            txns     = env['loyalty.transaction'].sudo().search([
                ('create_date', '>=', start),
                ('type', '=', 'earn'),
            ])
            loyalty_stats = {
                'total_accounts': len(accounts),
                'points_issued':  sum(t.points for t in txns),
                'levels': {
                    'starter':  len(accounts.filtered(lambda a: a.level == 'starter')),
                    'silver':   len(accounts.filtered(lambda a: a.level == 'silver')),
                    'gold':     len(accounts.filtered(lambda a: a.level == 'gold')),
                    'platinum': len(accounts.filtered(lambda a: a.level == 'platinum')),
                    'elite':    len(accounts.filtered(lambda a: a.level == 'elite')),
                },
            }

        # ── State Distribution ─────────────────────────────────────────────
        state_dist = {}
        for s in sessions:
            st = s.last_state or 'idle'
            state_dist[st] = state_dist.get(st, 0) + 1

        return {
            'period': period,
            'ai': {
                'total_sessions':   total_sessions,
                'happy_sessions':   happy_sessions,
                'sad_sessions':     sad_sessions,
                'conversion_rate':  ai_conversion,
                'sessions_chart':   sessions_chart,
                'state_dist':       state_dist,
            },
            'sales': {
                'total_revenue':    round(total_revenue, 3),
                'total_orders':     total_orders,
                'avg_order_value':  avg_order_value,
                'revenue_chart':    revenue_chart,
                'top_products':     top_products,
            },
            'reviewers': reviewer_stats,
            'loyalty':   loyalty_stats,
        }
