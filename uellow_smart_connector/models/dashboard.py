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

        # Publish Studio — new products on the way to the catalog
        def _sc(model, domain):
            """Safe search_count: never let one feature break the dashboard."""
            try:
                return env[model].sudo().search_count(domain)
            except Exception:
                return 0

        studio = {
            'pending': _sc('uellow.import.job.line',
                           [('product_action', '=', 'new'),
                            ('line_state', '!=', 'applied')]),
            'ready': _sc('uellow.import.job.line',
                         [('product_action', '=', 'new'),
                          ('line_state', '!=', 'applied'),
                          ('pub_ready', '=', True)]),
            'published': _sc('uellow.import.job.line',
                             [('product_action', '=', 'new'),
                              ('line_state', '=', 'applied')]),
        }

        # Reorder forecast
        reorder = {
            'total': _sc('uellow.sc.reorder.forecast',
                         [('state', 'in', ('urgent', 'reorder'))]),
            'urgent': _sc('uellow.sc.reorder.forecast', [('state', '=', 'urgent')]),
            'reorder': _sc('uellow.sc.reorder.forecast', [('state', '=', 'reorder')]),
        }

        # Supplier scorecard
        scorecard = {
            'vendors': _sc('uellow.sc.supplier.scorecard', []),
            'grade_a': _sc('uellow.sc.supplier.scorecard', [('grade', '=', 'a')]),
            'poor': _sc('uellow.sc.supplier.scorecard', [('grade', 'in', ('c', 'd'))]),
        }

        # Competitor discovery (opportunity radar)
        discovery = {
            'opportunities': _sc('uellow.sc.discovery', [('state', '=', 'new')]),
            'sources': _sc('uellow.sc.competitor.source', [('active', '=', True)]),
        }

        # Multi-market pricing + translation glossary
        market = {
            'factors': _sc('uellow.sc.market.factor', [('active', '=', True)]),
            'runs': _sc('uellow.sc.market.pricer', []),
        }
        glossary_terms = _sc('uellow.sc.glossary', [('active', '=', True)])

        # Profit margins — avg margin + count of losing products (bounded read)
        profit = {'count': 0, 'avg_margin': 0.0, 'negative': 0}
        try:
            prof_recs = env['product.template'].sudo().search_read(
                [('active', '=', True), ('sale_ok', '=', True)],
                ['list_price', 'standard_price'], limit=20000)
            margins, neg = [], 0
            for r in prof_recs:
                price = r['list_price'] or 0.0
                cost = r['standard_price'] or 0.0
                if price > 0:
                    margins.append((price - cost) / price * 100.0)
                    if (price - cost) < 0:
                        neg += 1
                elif cost > 0:
                    neg += 1  # price 0 but has cost = losing
            profit = {
                'count': len(prof_recs),
                'avg_margin': round(sum(margins) / len(margins), 1) if margins else 0.0,
                'negative': neg,
            }
        except Exception:
            pass

        # Price Intelligence
        price_records = env['uellow.price.intelligence'].sudo()
        total_monitored = price_records.search_count([])
        pricier_count = price_records.search_count([('state', '=', 'pricier')])
        cheaper_count = price_records.search_count([('state', '=', 'cheaper')])
        opportunity_count = price_records.search_count([('opportunity', '=', True)])

        # Dead Stock
        dead_stock = env['uellow.dead.stock'].sudo()
        total_dead = dead_stock.search_count([])
        critical_dead = dead_stock.search_count([('suggested_action', '=', 'discount')])
        seasonal_dead = dead_stock.search_count([('is_seasonal', '=', True)])
        promote_dead = dead_stock.search_count(
            [('beena_promote', '=', True), ('state', '=', 'active')])
        # idle-capital estimate (bounded loop so the dashboard stays cheap)
        dead_value = 0.0
        for r in dead_stock.search([('state', '=', 'active')], limit=2000):
            price = r.product_id.standard_price or r.product_id.lst_price or 0.0
            dead_value += (r.qty_on_hand or 0.0) * price

        # Translation coverage — read the latest job's snapshot (no heavy scan)
        tjob = env['uellow.sc.translate.job'].sudo().search([], limit=1,
                                                            order='create_date desc')
        translation = {
            'coverage': round(tjob.coverage_pct, 1) if tjob else 0.0,
            'translated': tjob.done_count if tjob else 0,
            'pending': tjob.total_count if tjob else 0,
        }

        # Recent jobs
        # B7: order by create_date — write_date reorders silently every time
        # _compute_stats touches the parent record, surprising the manager.
        recent_jobs = jobs.search([], limit=5, order='create_date desc')
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

        # Urgent reorders (top 5)
        urgent_reorders = []
        try:
            for r in env['uellow.sc.reorder.forecast'].sudo().search(
                    [('state', 'in', ('urgent', 'reorder'))],
                    limit=5, order='days_to_runout asc'):
                urgent_reorders.append({
                    'id': r.id,
                    'product': r.product_id.name or '',
                    'days': r.days_to_runout,
                    'qty': r.suggested_qty,
                    'state': r.state,
                })
        except Exception:
            pass

        # New competitor opportunities (top 5)
        opportunities = []
        try:
            for d in env['uellow.sc.discovery'].sudo().search(
                    [('state', '=', 'new')], limit=5, order='match_score asc'):
                opportunities.append({
                    'id': d.id,
                    'title': d.title or '',
                    'source': d.source_id.name if d.source_id else '',
                    'price': d.price,
                    'match': d.match_score,
                })
        except Exception:
            pass

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
            'studio': studio,
            'reorder': reorder,
            'scorecard': scorecard,
            'discovery': discovery,
            'market': market,
            'glossary': glossary_terms,
            'profit': profit,
            'price_intel': {
                'monitored': total_monitored,
                'pricier': pricier_count,
                'cheaper': cheaper_count,
                'opportunity': opportunity_count,
            },
            'dead_stock': {
                'total': total_dead,
                'critical': critical_dead,
                'seasonal': seasonal_dead,
                'promote': promote_dead,
                'value_kd': round(dead_value, 2),
            },
            'translation': translation,
            'recent_jobs': recent_jobs_data,
            'price_alerts': price_alerts_data,
            'urgent_reorders': urgent_reorders,
            'opportunities': opportunities,
        }
