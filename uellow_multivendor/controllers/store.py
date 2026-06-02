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

        if vendor.settings_id:
            store_page = request.env['uellow.vendor.store'].sudo().search([
                ('vendor_id', '=', vendor.id)], limit=1)
            if store_page:
                store_page.sudo().action_visit()

        base_domain = [
            ('vendor_id', '=', vendor.id),
            ('vendor_approval_state', '=', 'approved'),
        ]
        if search:
            base_domain += [('name', 'ilike', search)]

        all_products = request.env['product.template'].sudo().search(base_domain)

        # New in — sorted by create_date desc
        new_products = request.env['product.template'].sudo().search(
            base_domain, order='create_date desc', limit=6)

        # Best selling — sales_count is non-stored, so sort in Python
        best_selling = request.env['product.template'].sudo().search(
            base_domain).sorted(key=lambda p: p.sales_count, reverse=True)[:6]

        # Flash sales
        try:
            flash_products = request.env['product.template'].sudo().search(
                base_domain + [('is_flash_sale', '=', True)], order='create_date desc', limit=6)
        except Exception:
            flash_products = request.env['product.template'].sudo().browse([])

        # Categories
        categories = []
        try:
            cats = all_products.mapped('public_categ_ids')
            categories = list({c.id: c for c in cats}.values())
        except Exception:
            pass

        # Products by category
        category_sections = []
        for cat in categories[:6]:
            cat_products = request.env['product.template'].sudo().search(
                base_domain + [('public_categ_ids', '=', cat.id)], order='create_date desc', limit=6)
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

        _logger.info("STORE DEBUG: vendor=%s all=%s new=%s", vendor.id, len(all_products), len(new_products))
        flash_sale = request.env['uellow.flash.sale'].sudo().search(
            [('vendor_id', '=', vendor.id), ('state', '=', 'active')],
            order='end_datetime asc', limit=1)
        flash_seconds = flash_sale.remaining_seconds if flash_sale else 0
        style = vendor.settings_id.get_style() if vendor.settings_id else {
            'flash_bg': vendor.brand_color or '#c0392b', 'flash_accent': '#ffd60a',
            'section_title': vendor.brand_color or '#1A7A6E', 'price': '#1A7A6E', 'badge': '#c0392b', 'header_text': '#ffffff'}
        return request.render('uellow_multivendor.store_page', {
            'vendor': vendor,
            'all_products': all_products,
            'new_products': new_products,
            'best_selling': best_selling,
            'flash_products': flash_products,
            'flash_seconds': flash_seconds,
            'style': style,
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
