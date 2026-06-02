"""Wishlist — /api/mobile/v2/wishlist/*"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail, current_partner, require_auth, get_lang
from .products import serialize_product_card


class MobileWishlistAPI(http.Controller):

    @http.route('/api/mobile/v2/wishlist', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_wishlist(self, **kw):
        lang = get_lang()
        partner = current_partner()
        items = request.env['product.wishlist'].sudo().search([
            ('partner_id', '=', partner.id),
            ('active', '=', True),
        ])
        return ok([serialize_product_card(w.product_id.product_tmpl_id, lang)
                   for w in items if w.product_id and w.product_id.product_tmpl_id.is_published])

    @http.route('/api/mobile/v2/wishlist/add', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def add_wishlist(self, **kw):
        p = get_payload()
        partner = current_partner()
        try:
            tmpl_id = int(p.get('product_id') or 0)
        except Exception:
            return fail('BAD_REQUEST', 'product_id required')
        tmpl = request.env['product.template'].sudo().browse(tmpl_id)
        if not tmpl.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        variant = tmpl.product_variant_ids[:1]
        if not variant:
            return fail('NO_VARIANT', 'Product has no variants', 400)
        existing = request.env['product.wishlist'].sudo().search([
            ('partner_id', '=', partner.id),
            ('product_id', '=', variant.id),
        ], limit=1)
        if existing:
            existing.active = True
        else:
            website = request.env['website'].sudo().search([], limit=1)
            request.env['product.wishlist'].sudo().create({
                'partner_id': partner.id,
                'product_id': variant.id,
                'currency_id': variant.currency_id.id,
                'price': variant.list_price,
                'website_id': website.id,
            })
        return ok({'added': True})

    @http.route('/api/mobile/v2/wishlist/remove', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def remove_wishlist(self, **kw):
        p = get_payload()
        partner = current_partner()
        try:
            tmpl_id = int(p.get('product_id') or 0)
        except Exception:
            return fail('BAD_REQUEST', 'product_id required')
        tmpl = request.env['product.template'].sudo().browse(tmpl_id)
        variant_ids = tmpl.product_variant_ids.ids if tmpl.exists() else []
        items = request.env['product.wishlist'].sudo().search([
            ('partner_id', '=', partner.id),
            ('product_id', 'in', variant_ids),
        ])
        if items:
            items.unlink()
        return ok({'removed': True})
