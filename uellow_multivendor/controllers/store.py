import logging
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class VendorStoreController(http.Controller):
    """Public vendor store pages — /store/{slug}"""

    @http.route('/store/<string:slug>', type='http', auth='public', website=True)
    def store_page(self, slug, search='', tab='new_in', **kw):
        vendor = request.env['uellow.vendor'].sudo().search([
            ('store_slug', '=', slug),
            ('state', '=', 'active'),
        ], limit=1)
        if not vendor:
            return request.not_found()

        store = vendor.settings_id
        if store and not store.store_page_enabled:
            return request.not_found()

        if vendor.settings_id:
            store_page = request.env['uellow.vendor.store'].sudo().search([
                ('vendor_id', '=', vendor.id)], limit=1)
            if store_page:
                store_page.sudo().action_visit()

        base_domain = [
            ('vendor_id', '=', vendor.id),
            ('website_published', '=', True),
        ]
        if search:
            base_domain += [('name', 'ilike', search)]

        all_products = request.env['product.template'].sudo().search(base_domain)

        # New in — last 30 days
        month_ago = datetime.now() - timedelta(days=30)
        new_products = all_products.filtered(
            lambda p: p.create_date and p.create_date >= month_ago
        )[:8]

        # Best selling — by sales count
        best_selling = request.env['product.template'].sudo().search(
            base_domain, order='sales_count desc', limit=8)

        # Flash sales
        flash_products = all_products.filtered(lambda p: p.is_flash_sale)[:8]

        # Categories from vendor products
        categories = all_products.mapped('categ_id')
        categories = list({c.id: c for c in categories}.values())

        # Products by category (max 4 per category for sections)
        category_sections = []
        for cat in categories[:6]:
            cat_products = all_products.filtered(
                lambda p, c=cat: p.categ_id.id == c.id)[:4]
            if cat_products:
                category_sections.append({
                    'category': cat,
                    'products': cat_products,
                })

        # Check following
        is_following = False
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            is_following = bool(request.env['uellow.vendor.follower'].sudo().search([
                ('vendor_id', '=', vendor.id),
                ('partner_id', '=', request.env.user.partner_id.id),
            ]))

        return request.render('uellow_multivendor.store_page', {
            'vendor': vendor,
            'all_products': all_products,
            'new_products': new_products,
            'best_selling': best_selling,
            'flash_products': flash_products,
            'categories': categories,
            'category_sections': category_sections,
            'search': search,
            'tab': tab,
            'is_following': is_following,
            'page_name': 'vendor_store',
        })

    @http.route('/store/<string:slug>/follow', type='json', auth='user', website=True)
    def store_follow(self, slug, **kw):
        vendor = request.env['uellow.vendor'].sudo().search([
            ('store_slug', '=', slug), ('state', '=', 'active')], limit=1)
        if not vendor:
            return {'error': 'not found'}
        follower = request.env['uellow.vendor.follower'].sudo().search([
            ('vendor_id', '=', vendor.id),
            ('partner_id', '=', request.env.user.partner_id.id),
        ])
        if follower:
            follower.unlink()
            return {'following': False}
        else:
            request.env['uellow.vendor.follower'].sudo().create({
                'vendor_id': vendor.id,
                'partner_id': request.env.user.partner_id.id,
            })
            return {'following': True}

    @http.route('/store/<string:slug>/about', type='http', auth='public', website=True)
    def store_about(self, slug, **kw):
        vendor = request.env['uellow.vendor'].sudo().search([
            ('store_slug', '=', slug),
            ('state', '=', 'active'),
        ], limit=1)
        if not vendor:
            return request.not_found()
        return request.render('uellow_multivendor.store_about', {
            'vendor': vendor,
            'page_name': 'vendor_store',
        })
