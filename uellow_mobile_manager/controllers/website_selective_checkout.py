# -*- coding: utf-8 -*-
"""Website selective checkout (v2.1.69) — mirror of the app feature:
the customer ticks cart lines and pays for ONLY those; the rest stays
in the cart. Reuses the SAME split engine the mobile API uses, so
shipping, coupons and payment behave identically.

Flow:
  POST /shop/cart/checkout-selected {line_ids[]} → split the session
  order (unselected lines move to a fresh draft kept in the session as
  `uellow_split_remainder_id`) → redirect to /shop/checkout.
  • Payment completes → Odoo clears the session order → next /shop/cart
    visit restores the remainder as the active cart.
  • Customer backs out to /shop/cart instead → the split is undone
    (remainder merged back) so the full cart reappears.
"""
import logging

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

from .api_v2.cart import split_cart_for_checkout

_logger = logging.getLogger(__name__)

_SESSION_KEY = 'uellow_split_remainder_id'


class UellowWebsiteSelectiveCheckout(http.Controller):

    @http.route('/shop/cart/checkout-selected', type='http', auth='public',
                methods=['POST'], csrf=True, website=True)
    def checkout_selected(self, **post):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect('/shop/cart')
        ids = []
        for raw in request.httprequest.form.getlist('line_ids'):
            try:
                ids.append(int(raw))
            except Exception:
                continue
        if ids:
            try:
                remainder = split_cart_for_checkout(order, ids)
                if remainder is not None:
                    request.session[_SESSION_KEY] = remainder.id
            except ValueError:
                pass            # stale selection → checkout the full cart
            except Exception:
                _logger.exception('website selective checkout split failed')
        return request.redirect('/shop/checkout')


class WebsiteSaleSplitAware(WebsiteSale):

    @http.route()
    def cart(self, **post):
        """Entering the cart page settles any pending split:
        • session order gone/confirmed → remainder becomes the cart
        • session order still draft+split → user backed out → merge the
          remainder back so the FULL cart reappears."""
        try:
            self._uellow_settle_split()
        except Exception:
            _logger.debug('split settle failed', exc_info=True)
        return super().cart(**post)

    def _uellow_settle_split(self):
        rid = request.session.get(_SESSION_KEY)
        if not rid:
            return
        Order = request.env['sale.order'].sudo()
        remainder = Order.browse(rid)
        if not remainder.exists() or remainder.state != 'draft' \
                or not remainder.order_line:
            request.session.pop(_SESSION_KEY, None)
            return
        order = request.website.sale_get_order()
        if order and order.state == 'draft' and \
                getattr(order, 'mobile_checkout_split', False):
            # Backed out of checkout → undo the split.
            for l in remainder.order_line.filtered(
                    lambda l: not l.display_type and not l.is_reward_line
                    and not getattr(l, 'is_delivery', False)):
                same = order.order_line.filtered(
                    lambda x: x.product_id == l.product_id
                    and not x.display_type and not x.is_reward_line)
                if same:
                    same[0].product_uom_qty += l.product_uom_qty
                else:
                    l.write({'order_id': order.id})
            order.write({'mobile_checkout_split': False})
            try:
                remainder.action_cancel()
            except Exception:
                pass
            remainder.unlink()
            try:
                if hasattr(order, '_update_programs_and_rewards'):
                    order._update_programs_and_rewards()
            except Exception:
                pass
        elif not order or order.state != 'draft' or not order.order_line:
            # Paid (or cart gone) → the remainder IS the new cart.
            request.session['sale_order_id'] = remainder.id
        request.session.pop(_SESSION_KEY, None)
