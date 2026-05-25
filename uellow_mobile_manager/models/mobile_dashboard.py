# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class MobileDashboard(models.Model):
    _name = 'mobile.dashboard'
    _description = 'Mobile App Dashboard (virtual)'

    # Virtual model — no DB table, just computed data
    name = fields.Char(default='Dashboard')

    @api.model
    def get_dashboard_data(self, website_id=None):
        """Return all KPIs for the dashboard."""
        env = self.env
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)
        threshold_30min = now - timedelta(minutes=30)

        ws_domain = [('website_id', '=', int(website_id))] if website_id else []

        # ── Sessions ─────────────────────────────────────────────────
        SessionModel = env['mobile.session'].sudo()
        active_now = SessionModel.search_count(
            [('last_activity', '>=', threshold_30min)] + ws_domain
        )
        sessions_today = SessionModel.search_count(
            [('last_activity', '>=', today_start)] + ws_domain
        )
        sessions_week = SessionModel.search_count(
            [('last_activity', '>=', week_start)] + ws_domain
        )
        sessions_month = SessionModel.search_count(
            [('last_activity', '>=', month_start)] + ws_domain
        )
        total_users = SessionModel.search_count(
            [('is_guest', '=', False)] + ws_domain
        )
        guest_users = SessionModel.search_count(
            [('is_guest', '=', True)] + ws_domain
        )
        android_count = SessionModel.search_count(
            [('platform', '=', 'android')] + ws_domain
        )
        ios_count = SessionModel.search_count(
            [('platform', '=', 'ios')] + ws_domain
        )

        # ── Orders from App ───────────────────────────────────────────
        OrderModel = env['mobile.app.order'].sudo()
        orders_today = OrderModel.search_count(
            [('order_date', '>=', today_start)] + ws_domain
        )
        orders_week = OrderModel.search_count(
            [('order_date', '>=', week_start)] + ws_domain
        )
        orders_month = OrderModel.search_count(
            [('order_date', '>=', month_start)] + ws_domain
        )

        # Revenue from app
        env.cr.execute("""
            SELECT COALESCE(SUM(amount_total), 0) as revenue
            FROM mobile_app_order
            WHERE order_date >= %s
            AND state NOT IN ('cancel', 'draft')
        """, (month_start,))
        revenue_month = env.cr.fetchone()[0]

        env.cr.execute("""
            SELECT COALESCE(SUM(amount_total), 0) as revenue
            FROM mobile_app_order
            WHERE order_date >= %s
            AND state NOT IN ('cancel', 'draft')
        """, (today_start,))
        revenue_today = env.cr.fetchone()[0]

        # Average order value
        env.cr.execute("""
            SELECT COALESCE(AVG(amount_total), 0) as avg
            FROM mobile_app_order
            WHERE order_date >= %s AND state NOT IN ('cancel', 'draft')
        """, (month_start,))
        avg_order_value = env.cr.fetchone()[0]

        # Orders by source
        env.cr.execute("""
            SELECT order_source, COUNT(*) as count
            FROM mobile_app_order
            WHERE order_date >= %s
            GROUP BY order_source ORDER BY count DESC
        """, (month_start,))
        orders_by_source = env.cr.dictfetchall()

        # ── Session chart (last 7 days) ───────────────────────────────
        env.cr.execute("""
            SELECT DATE(last_activity) as day, COUNT(*) as count
            FROM mobile_session
            WHERE last_activity >= %s
            GROUP BY day ORDER BY day ASC
        """, (week_start,))
        sessions_chart = env.cr.dictfetchall()

        # ── Top searched keywords ─────────────────────────────────────
        top_searches = []
        if env['ir.model'].sudo().search([('model', '=', 'mobile.search.analytic')], limit=1):
            top_searches = env['mobile.search.analytic'].sudo().get_top_keywords(10, 30)

        # ── Notifications ─────────────────────────────────────────────
        NotifModel = env['mobile.notification'].sudo()
        notif_sent = NotifModel.search_count([('state', '=', 'sent')] + ws_domain)
        notif_draft = NotifModel.search_count([('state', '=', 'draft')] + ws_domain)

        # ── App version breakdown ─────────────────────────────────────
        env.cr.execute("""
            SELECT app_version, COUNT(*) as count
            FROM mobile_session
            WHERE app_version IS NOT NULL AND app_version != ''
            GROUP BY app_version ORDER BY count DESC LIMIT 5
        """)
        version_breakdown = env.cr.dictfetchall()

        # ── Platform breakdown (for donut chart) ─────────────────────
        total_sessions = android_count + ios_count or 1
        android_pct = round(android_count / total_sessions * 100)
        ios_pct = 100 - android_pct

        return {
            'sessions': {
                'active_now': active_now,
                'today': sessions_today,
                'week': sessions_week,
                'month': sessions_month,
                'chart': [{'day': str(r['day']), 'count': r['count']} for r in sessions_chart],
            },
            'users': {
                'total_registered': total_users,
                'guests': guest_users,
                'android': android_count,
                'ios': ios_count,
                'android_pct': android_pct,
                'ios_pct': ios_pct,
                'version_breakdown': version_breakdown,
            },
            'orders': {
                'today': orders_today,
                'week': orders_week,
                'month': orders_month,
                'revenue_today': round(revenue_today, 2),
                'revenue_month': round(revenue_month, 2),
                'avg_order_value': round(avg_order_value, 2),
                'by_source': orders_by_source,
            },
            'notifications': {
                'sent': notif_sent,
                'draft': notif_draft,
            },
            'top_searches': top_searches,
        }
