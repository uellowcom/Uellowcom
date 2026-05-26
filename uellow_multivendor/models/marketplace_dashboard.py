from odoo import models, api
from datetime import datetime, timedelta


class MarketplaceDashboard(models.TransientModel):
    _name = 'uellow.marketplace.dashboard'
    _description = 'Marketplace Dashboard'

    @api.model
    def get_dashboard_data(self):
        env = self.env
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        orders = env['sale.order'].sudo()
        month_orders = orders.search([
            ('state', 'in', ['sale', 'done']),
            ('date_order', '>=', month_start),
        ])
        gmv = sum(month_orders.mapped('amount_total'))
        order_count = len(month_orders)
        cancel_orders = orders.search_count([('state', '=', 'cancel'), ('date_order', '>=', month_start)])
        cancel_rate = round(cancel_orders / (order_count + cancel_orders) * 100, 1) if (order_count + cancel_orders) else 0

        days_data = []
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            day_orders = orders.search([('state', 'in', ['sale', 'done']), ('date_order', '>=', day_start), ('date_order', '<=', day_end)])
            days_data.append({'day': day.strftime('%a'), 'gmv': round(sum(day_orders.mapped('amount_total')), 3), 'orders': len(day_orders)})

        vendors = env['uellow.vendor'].sudo()
        active_vendors = vendors.search_count([('state', '=', 'active')])
        pending_vendors = vendors.search_count([('state', '=', 'pending')])

        top_vendors_data = []
        for v in vendors.search([('state', '=', 'active')], limit=5):
            v_orders = orders.search([('vendor_id', '=', v.id), ('state', 'in', ['sale', 'done']), ('date_order', '>=', month_start)])
            top_vendors_data.append({'name': v.store_name_en or v.partner_id.name, 'gmv': round(sum(v_orders.mapped('amount_total')), 3)})
        top_vendors_data.sort(key=lambda x: x['gmv'], reverse=True)

        commissions = env['uellow.vendor.commission'].sudo()
        month_commission = sum(commissions.search([('create_date', '>=', month_start)]).mapped('commission_amount'))
        take_rate = round(month_commission / gmv * 100, 1) if gmv else 0

        products = env['product.template'].sudo()
        approved_products = products.search_count([('vendor_id', '!=', False), ('vendor_approval_state', '=', 'approved')])
        pending_products = products.search_count([('vendor_id', '!=', False), ('vendor_approval_state', '=', 'pending')])

        payouts = env['uellow.vendor.payout'].sudo()
        pending_payouts = payouts.search([('state', '=', 'pending')])
        pending_payout_amount = sum(pending_payouts.mapped('amount'))

        sc_jobs = env['uellow.import.job'].sudo()
        sc_total = sc_jobs.search_count([])
        sc_review = sc_jobs.search_count([('state', '=', 'review')])
        sc_imported = env['uellow.import.job.line'].sudo().search_count([('line_state', '=', 'applied')])
        sc_price_alerts = env['uellow.price.intelligence'].sudo().search_count([('state', '=', 'pricier')])
        sc_dead = env['uellow.dead.stock'].sudo().search_count([])

        reviews = env['rating.rating'].sudo()
        month_reviews = reviews.search_count([('create_date', '>=', month_start)])
        all_reviews = reviews.search([])
        avg_rating = round(sum(all_reviews.mapped('rating')) / len(all_reviews), 1) if all_reviews else 0

        return {
            'gmv': round(gmv, 3),
            'order_count': order_count,
            'cancel_rate': cancel_rate,
            'active_vendors': active_vendors,
            'pending_vendors': pending_vendors,
            'commission': round(month_commission, 3),
            'take_rate': take_rate,
            'approved_products': approved_products,
            'pending_products': pending_products,
            'pending_payout_amount': round(pending_payout_amount, 3),
            'pending_payouts': len(pending_payouts),
            'avg_rating': avg_rating,
            'days_data': days_data,
            'top_vendors': top_vendors_data[:5],
            'sc_total': sc_total,
            'sc_review': sc_review,
            'sc_imported': sc_imported,
            'sc_price_alerts': sc_price_alerts,
            'sc_dead': sc_dead,
            'month_reviews': month_reviews,
            'avg_product_rating': avg_rating,
            'pending_reviews': 0,
        }
