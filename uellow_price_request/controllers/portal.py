# -*- coding: utf-8 -*-
"""Vendor-portal pages for price-update requests.

A merchant logs into /my/vendor and sees the requests addressed to them.
Per line they tap **Match** (keep the current price) or type a new price,
then submit. Matched / unchanged lines auto-confirm; changed lines go to
the buyer's approval inbox (handled by uellow.price.request.submit_response).
"""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VendorPriceRequestPortal(http.Controller):

    def _get_vendor(self):
        if request.env.user._is_public():
            return False
        Vendor = request.env['uellow.vendor'].sudo()
        vendor = Vendor.search([('user_id', '=', request.env.user.id)], limit=1)
        if not vendor:
            vendor = Vendor.search(
                [('partner_id', '=', request.env.user.partner_id.id)], limit=1)
        return vendor

    def _requests_for(self, vendor):
        return request.env['uellow.price.request'].sudo().search(
            [('merchant_id', '=', vendor.id),
             ('state', 'in', ('sent', 'received', 'applied'))],
            order='create_date desc')

    @http.route('/my/vendor/price-requests', type='http', auth='user',
                website=True)
    def price_requests(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        return request.render(
            'uellow_price_request.portal_price_requests', {
                'vendor': vendor,
                'requests': self._requests_for(vendor),
                'page_name': 'vendor_price_requests',
            })

    @http.route('/my/vendor/price-requests/<int:req_id>', type='http',
                auth='user', website=True)
    def price_request_detail(self, req_id, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        req = request.env['uellow.price.request'].sudo().browse(req_id)
        if not req.exists() or req.merchant_id.id != vendor.id:
            return request.redirect('/my/vendor/price-requests')
        return request.render(
            'uellow_price_request.portal_price_request_detail', {
                'vendor': vendor,
                'req': req,
                'page_name': 'vendor_price_requests',
                'saved': kw.get('saved'),
            })

    @http.route('/my/vendor/price-requests/<int:req_id>/submit', type='http',
                auth='user', website=True, methods=['POST'], csrf=True)
    def price_request_submit(self, req_id, **post):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        req = request.env['uellow.price.request'].sudo().browse(req_id)
        if not req.exists() or req.merchant_id.id != vendor.id:
            return request.redirect('/my/vendor/price-requests')
        responses = []
        for ln in req.line_ids:
            keep = post.get('keep_%s' % ln.id)
            oos = post.get('oos_%s' % ln.id)
            raw = (post.get('price_%s' % ln.id) or '').strip()
            if oos:
                responses.append({'line_id': ln.id, 'action': 'oos'})
            elif keep:
                responses.append({'line_id': ln.id, 'action': 'match'})
            elif raw:
                try:
                    responses.append({'line_id': ln.id, 'action': 'price',
                                      'price': float(raw)})
                except ValueError:
                    continue
        if responses:
            req.submit_response(responses)
            request.env.cr.commit()
        return request.redirect(
            '/my/vendor/price-requests/%s?saved=1' % req_id)
