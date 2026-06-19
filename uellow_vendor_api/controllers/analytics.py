# -*- coding: utf-8 -*-
"""Vendor analytics — /api/vendor/v1/analytics*"""
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, require_auth, current_vendor, fmt_price,
    bilingual, img_url,
)


class VendorAnalyticsAPI(http.Controller):

    @http.route('/api/vendor/v1/analytics/kpis', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def kpis(self, **kw):
        """Operational KPIs for the vendor: products, categories, views,
        profit/margin, sales & customers."""
        v = current_vendor()
        cur = v.currency_id
        Tmpl = request.env['product.template'].sudo()
        Order = request.env['sale.order'].sudo()
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        prods = Tmpl.search([('vendor_id', '=', v.id)])
        published = prods.filtered(lambda t: t.is_published and t.vendor_approval_state == 'approved')
        pending = prods.filtered(lambda t: t.vendor_approval_state in ('draft', 'pending'))
        oos = prods.filtered(lambda t: t.is_storable and (t.qty_available or 0) <= 0)
        low = prods.filtered(lambda t: t.is_storable and 0 < (t.qty_available or 0) <= 5)
        total_views = sum(prods.mapped('uellow_view_count'))

        # Inventory held at Yellow (FBU / consignment) — valued at cost.
        fbu_value = fbu_units = 0.0
        fbu_loc = v.fbu_location_id.location_id if v.fbu_location_id else False
        if fbu_loc:
            quants = request.env['stock.quant'].sudo().search(
                [('location_id', 'child_of', fbu_loc.id), ('quantity', '>', 0)])
            for q in quants:
                fbu_units += q.quantity or 0.0
                fbu_value += (q.quantity or 0.0) * (q.product_id.standard_price or 0.0)

        # Top viewed products
        top_viewed = prods.sorted(lambda t: t.uellow_view_count or 0, reverse=True)[:5]

        # Confirmed orders (all-time + this month) for profit + sales
        confirmed = Order.search([('vendor_id', '=', v.id), ('state', 'in', ('sale', 'done'))])
        revenue = cost = 0.0
        cat_rev, cat_units = {}, {}
        prod_units = {}
        month_gmv = 0.0
        month_orders = 0
        cust_counts = {}
        for o in confirmed:
            base = o.date_order or o.create_date
            in_month = bool(base) and base >= month_start
            if in_month:
                month_gmv += o.amount_total or 0
                month_orders += 1
            cust_counts[o.partner_id.id] = cust_counts.get(o.partner_id.id, 0) + 1
            for l in o.order_line.filtered(lambda l: not l.display_type and l.product_id):
                sub = l.price_subtotal or 0.0
                c = (l.product_id.standard_price or 0.0) * (l.product_uom_qty or 0.0)
                revenue += sub
                cost += c
                tmpl = l.product_id.product_tmpl_id
                prod_units[tmpl.id] = prod_units.get(tmpl.id, 0.0) + (l.product_uom_qty or 0.0)
                categ = tmpl.public_categ_ids[:1]
                if categ:
                    cat_rev[categ.id] = cat_rev.get(categ.id, 0.0) + sub
                    cat_units[categ.id] = cat_units.get(categ.id, 0.0) + (l.product_uom_qty or 0.0)
        gross = revenue - cost
        margin_pct = round(gross / revenue * 100, 1) if revenue else 0.0
        distinct = len(cust_counts)
        repeat = sum(1 for c in cust_counts.values() if c > 1)

        # Top categories by revenue
        Cat = request.env['product.public.category'].sudo()
        top_cats = sorted(cat_rev.items(), key=lambda kv: kv[1], reverse=True)[:6]
        categories = []
        for cid, rev in top_cats:
            c = Cat.browse(cid)
            categories.append({
                'id': cid, 'name': bilingual(c, 'name'),
                'revenue': fmt_price(rev, cur),
                'units': int(cat_units.get(cid, 0)),
            })

        # Top selling products (by units)
        top_sellers = sorted(prod_units.items(), key=lambda kv: kv[1], reverse=True)[:5]
        sellers = []
        for tid, units in top_sellers:
            t = Tmpl.browse(tid)
            sellers.append({
                'id': tid, 'name': bilingual(t, 'name'),
                'units': int(units),
                'views': int(t.uellow_view_count or 0),
                'image_url': img_url('product.template', t.id, 'image_128',
                                     unique=t.write_date) if t.image_128 else None,
            })

        aov = (month_gmv / month_orders) if month_orders else 0.0
        is_fbu = (v.vendor_type or 'seller') in ('fbu', 'consignment')
        return ok({
            'vendor_type': v.vendor_type or 'seller',
            'inventory': {
                'value': fmt_price(fbu_value, cur),
                'units': int(fbu_units),
                'is_fbu': is_fbu,
                'location': fbu_loc.complete_name if fbu_loc else '',
            },
            'products': {
                'total': len(prods), 'published': len(published),
                'pending': len(pending), 'out_of_stock': len(oos),
                'low_stock': len(low), 'total_views': int(total_views),
            },
            'profit': {
                'revenue': fmt_price(revenue, cur),
                'cost': fmt_price(cost, cur),
                'gross_profit': fmt_price(gross, cur),
                'margin_pct': margin_pct,
            },
            'sales': {
                'gmv_month': fmt_price(month_gmv, cur),
                'orders_month': month_orders,
                'aov': fmt_price(aov, cur),
                'units_all': int(sum(prod_units.values())),
            },
            'customers': {
                'distinct': distinct, 'repeat': repeat,
                'repeat_pct': round(repeat / distinct * 100, 1) if distinct else 0.0,
            },
            'categories': categories,
            'top_sellers': sellers,
            'top_viewed': [{
                'id': t.id, 'name': bilingual(t, 'name'),
                'views': int(t.uellow_view_count or 0),
            } for t in top_viewed if (t.uellow_view_count or 0) > 0],
        })

    @http.route('/api/vendor/v1/analytics/sales', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def sales_timeseries(self, **kw):
        """Last N days of sales (default 30). Returns daily revenue + orders."""
        v = current_vendor()
        p = get_payload()
        try:
            days = max(7, min(90, int(p.get('days') or 30)))
        except (TypeError, ValueError):
            days = 30
        Order = request.env['sale.order'].sudo()
        start = datetime.now().date() - timedelta(days=days - 1)
        rows = Order.search([
            ('vendor_id', '=', v.id),
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', start),
        ])
        # Group by day
        buckets = {}
        for d in (start + timedelta(days=i) for i in range(days)):
            buckets[d.isoformat()] = {'revenue': 0.0, 'orders': 0}
        for o in rows:
            day = (o.date_order or o.create_date).date().isoformat()
            if day in buckets:
                buckets[day]['revenue'] += o.amount_total or 0
                buckets[day]['orders'] += 1
        return ok({
            'days': [{'date': k, **v} for k, v in buckets.items()],
            'total_revenue': sum(b['revenue'] for b in buckets.values()),
            'total_orders': sum(b['orders'] for b in buckets.values()),
        })

    @http.route('/api/vendor/v1/analytics/top-products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def top_products(self, **kw):
        v = current_vendor()
        Order = request.env['sale.order'].sudo()
        confirmed = Order.search([('vendor_id', '=', v.id),
                                   ('state', 'in', ('sale', 'done'))], limit=2000)
        totals = {}  # tmpl_id -> {revenue, qty, name}
        for o in confirmed:
            for l in o.order_line.filtered(lambda l: not l.display_type):
                tmpl = l.product_id.product_tmpl_id
                if tmpl.vendor_id.id != v.id:
                    continue
                t = totals.setdefault(tmpl.id, {
                    'tmpl': tmpl, 'revenue': 0.0, 'qty': 0.0,
                })
                t['revenue'] += l.price_subtotal or 0
                t['qty'] += l.product_uom_qty or 0
        rows = sorted(totals.values(), key=lambda x: -x['revenue'])[:20]
        cur = v.currency_id or request.env.company.currency_id
        return ok([{
            'id': r['tmpl'].id,
            'name': bilingual(r['tmpl'], 'name'),
            'image_url': img_url('product.template', r['tmpl'].id,
                                 'image_256', unique=r['tmpl'].write_date)
                          if r['tmpl'].image_1920 else None,
            'revenue': fmt_price(r['revenue'], cur),
            'qty': r['qty'],
        } for r in rows])

    @http.route('/api/vendor/v1/analytics/top-customers', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def top_customers(self, **kw):
        v = current_vendor()
        Order = request.env['sale.order'].sudo()
        confirmed = Order.search([('vendor_id', '=', v.id),
                                   ('state', 'in', ('sale', 'done'))], limit=2000)
        totals = {}
        for o in confirmed:
            t = totals.setdefault(o.partner_id.id, {
                'partner': o.partner_id, 'spent': 0.0, 'orders': 0,
            })
            t['spent'] += o.amount_total or 0
            t['orders'] += 1
        rows = sorted(totals.values(), key=lambda x: -x['spent'])[:20]
        cur = v.currency_id or request.env.company.currency_id
        return ok([{
            'id': r['partner'].id,
            'name': r['partner'].name,
            'spent': fmt_price(r['spent'], cur),
            'orders': r['orders'],
            'avatar_url': img_url('res.partner', r['partner'].id,
                                  'image_128', unique=r['partner'].write_date)
                          if r['partner'].image_128 else None,
        } for r in rows])
