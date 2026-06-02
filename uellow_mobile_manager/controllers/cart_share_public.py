"""Public share-cart landing — recipient opens /cart/share/<token> and
can adopt the items into their own cart."""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CartSharePublic(http.Controller):

    @http.route('/cart/share/<string:token>', type='http', auth='public',
                methods=['GET'], csrf=False, website=True)
    def view(self, token, **kw):
        share = request.env['mobile.cart.share'].sudo().search(
            [('token', '=', token), ('active', '=', True)], limit=1)
        if not share:
            return request.render('uellow_mobile_manager.cart_share_not_found', {})
        try:
            items = json.loads(share.lines_json or '[]')
        except Exception:
            items = []
        return request.render('uellow_mobile_manager.cart_share_view', {
            'share': share,
            'items': items,
            'count': len(items),
        })

    @http.route('/cart/share/<string:token>/adopt', type='http', auth='public',
                methods=['POST'], csrf=False, website=True)
    def adopt(self, token, **kw):
        share = request.env['mobile.cart.share'].sudo().search(
            [('token', '=', token), ('active', '=', True)], limit=1)
        if not share:
            return request.redirect('/shop')
        try:
            items = json.loads(share.lines_json or '[]')
        except Exception:
            items = []
        sale_order = request.website.sale_get_order(force_create=True)
        for it in items:
            try:
                pid = int(it.get('product_id'))
                qty = float(it.get('qty') or 1)
            except Exception:
                continue
            try:
                sale_order._cart_update(product_id=pid, add_qty=qty)
            except Exception as e:
                _logger.warning('Adopt share item failed pid=%s: %s', pid, e)
        share.adopted_count += 1
        return request.redirect('/shop/cart')
