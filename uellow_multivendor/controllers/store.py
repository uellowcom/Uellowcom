import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VendorStoreController(http.Controller):
    """Public vendor store pages — /store/{slug}"""

    @http.route('/store/<string:slug>', type='http', auth='public', website=True)
    def store_page(self, slug, search='', page=1, **kw):
        vendor = request.env['uellow.vendor'].sudo().search([
            ('store_slug', '=', slug),
            ('state', '=', 'active'),
        ], limit=1)
        if not vendor:
            return request.not_found()
        # Check store page enabled via vendor.store model
        store_rec = request.env['uellow.vendor.store'].sudo().search([
            ('vendor_id', '=', vendor.id)], limit=1)
        if store_rec and hasattr(store_rec, 'store_page_enabled') and not store_rec.store_page_enabled:
            return request.not_found()

        # Increment visit counter
        if vendor.settings_id:
            store_page = request.env['uellow.vendor.store'].sudo().search([
                ('vendor_id', '=', vendor.id)], limit=1)
            if store_page:
                store_page.sudo().action_visit()

        domain = [
            ('vendor_id', '=', vendor.id),
            ('website_published', '=', True),
        ]
        if search:
            domain += [('name', 'ilike', search)]

        products = request.env['product.template'].sudo().search(
            domain, limit=20, offset=(int(page)-1)*20)

        # Check if current user follows this vendor
        is_following = False
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            is_following = bool(request.env['uellow.vendor.follower'].sudo().search([
                ('vendor_id', '=', vendor.id),
                ('partner_id', '=', request.env.user.partner_id.id),
            ]))

        return request.render('uellow_multivendor.store_page', {
            'vendor': vendor,
            'products': products,
            'search': search,
            'is_following': is_following,
            'page_name': 'vendor_store',
        })

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
