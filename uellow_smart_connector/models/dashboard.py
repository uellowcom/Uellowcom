from odoo import models, fields, api


class SmartConnectorDashboard(models.TransientModel):
    """Dashboard KPIs for Smart Connector."""
    _name = 'uellow.sc.dashboard'
    _description = 'Smart Connector Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Return all KPI data for the dashboard."""
        env = self.env

        # Import Jobs stats
        jobs = env['uellow.import.job'].sudo()
        total_jobs = jobs.search_count([])
        jobs_review = jobs.search_count([('state', '=', 'review')])
        jobs_done = jobs.search_count([('state', '=', 'done')])
        jobs_error = jobs.search_count([('state', '=', 'error')])

        # Products imported
        lines = env['uellow.import.job.line'].sudo()
        total_products_imported = lines.search_count([('line_state', '=', 'applied')])
        pending_review = lines.search_count([('line_state', '=', 'pending')])
        ai_enriched = lines.search_count([('ai_enriched', '=', True)])

        # Price Intelligence
        price_records = env['uellow.price.intelligence'].sudo()
        total_monitored = price_records.search_count([])
        pricier_count = price_records.search_count([('state', '=', 'pricier')])
        cheaper_count = price_records.search_count([('state', '=', 'cheaper')])

        # Dead Stock
        dead_stock = env['uellow.dead.stock'].sudo()
        total_dead = dead_stock.search_count([])
        critical_dead = dead_stock.search_count([('suggested_action', '=', 'discount')])

        # Recent jobs
        recent_jobs = jobs.search([], limit=5, order='write_date desc')
        recent_jobs_data = []
        for job in recent_jobs:
            recent_jobs_data.append({
                'id': job.id,
                'name': job.name,
                'type': job.job_type,
                'state': job.state,
                'total': job.total_lines,
                'new': job.new_count,
                'date': job.write_date.strftime('%d/%m/%Y') if job.write_date else '',
            })

        # Recent price alerts
        price_alerts = price_records.search(
            [('state', 'in', ('pricier', 'cheaper'))],
            limit=5, order='write_date desc')
        price_alerts_data = []
        for p in price_alerts:
            price_alerts_data.append({
                'id': p.id,
                'product': p.product_id.name or '',
                'source': p.source_name or '',
                'our_price': p.our_price,
                'competitor_price': p.competitor_price,
                'diff': p.price_diff_pct,
                'state': p.state,
            })

        return {
            'jobs': {
                'total': total_jobs,
                'review': jobs_review,
                'done': jobs_done,
                'error': jobs_error,
            },
            'products': {
                'imported': total_products_imported,
                'pending': pending_review,
                'ai_enriched': ai_enriched,
            },
            'price_intel': {
                'monitored': total_monitored,
                'pricier': pricier_count,
                'cheaper': cheaper_count,
            },
            'dead_stock': {
                'total': total_dead,
                'critical': critical_dead,
            },
            'recent_jobs': recent_jobs_data,
            'price_alerts': price_alerts_data,
        }
