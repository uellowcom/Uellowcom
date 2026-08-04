# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from .main import _lines_from_ids, country_code

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return request.make_json_response(data, status=status)


class LammaMobile(http.Controller):
    """Mobile API for لمّة يلو (consumed by the Flutter app). Public, read-only,
    stateless — the app holds the bundle and asks the server to price it."""

    @http.route('/api/mobile/v2/lamma/config', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def config(self, **kw):
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        cur = request.env.company.currency_id
        return _json({
            'enabled': bool(cfg.active and cfg.enable_all_products
                            and cfg._country_enabled(kw.get('country') or country_code())),
            'label': cfg.brand_label,
            'badge': cfg.badge_text,
            'enable_all_products': cfg.enable_all_products,
            'replace_add_to_cart': cfg.replace_add_to_cart,
            'min_items': cfg.min_items,
            'discount_mode': cfg.discount_mode,
            'max_discount_pct': cfg.max_discount_pct,
            'min_margin_pct': cfg.min_margin_pct,
            'free_shipping_items': cfg.free_shipping_items,
            'tiers': [{'min_qty': t.min_qty, 'min_amount': t.min_amount,
                       'discount_pct': t.discount_pct} for t in cfg.tier_ids],
            'installment': {
                'enabled': cfg.installment_enabled,
                'extra_margin_pct': cfg.installment_extra_margin,
                'provider': cfg.installment_provider,
                'max_months': cfg.installment_max_months,
                'min_amount': cfg.installment_min_amount,
            },
            'currency': cur.symbol or cur.name or 'KD',
        })

    @http.route('/api/mobile/v2/lamma/quote', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def quote(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        try:
            payload = json.loads(request.httprequest.get_data() or b'{}')
        except Exception:
            payload = {}
        ids = payload.get('product_ids') or []
        ltype = payload.get('type') or 'normal'
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        prods, lines = _lines_from_ids(ids)
        q = cfg.compute_lamma(lines, ltype)
        cur = request.env.company.currency_id
        q['currency'] = cur.symbol or cur.name or 'KD'
        q['items'] = [{
            'id': p.id, 'name': p.name or '',
            'price': round(p.list_price or 0.0, 3),
            'image': '/web/image/product.template/%s/image_256' % p.id,
        } for p in prods]
        return _json(q)

    @http.route('/api/mobile/v2/lamma/checkout', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def app_checkout(self, **kw):
        """Add the Lamma products to the app cart with the server-recomputed,
        margin-protected discount. Reuses uellow_mobile_manager's order
        resolution (partner/guest cart) so it integrates with the app cart.
        The discount is re-derived here + via _recompute_lamma — never trusted
        from the client."""
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        try:
            payload = json.loads(request.httprequest.get_data() or b'{}')
        except Exception:
            payload = {}
        ids = payload.get('product_ids') or []
        ltype = payload.get('type') or 'normal'
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        prods, _lines = _lines_from_ids(ids)
        if len(prods) < max(1, cfg.min_items):
            _logger.info('lamma app checkout need_more: sent=%s resolved=%s min=%s',
                         ids, len(prods), cfg.min_items)
            return _json({'ok': False, 'error': 'need_more', 'min_items': cfg.min_items}, status=400)
        if not cfg._country_enabled(request.env.company.country_id.code or country_code()):
            return _json({'ok': False, 'error': 'disabled'}, status=403)
        try:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import _get_or_create_order
            q = cfg.compute_lamma(_lines, ltype)
            order = _get_or_create_order(create=True)
            if not order:
                return _json({'ok': False, 'error': 'no_order'}, status=500)
            Line = request.env['sale.order.line'].sudo()
            for p in prods:
                variant = p.product_variant_id
                if not variant:
                    continue
                existing = order.order_line.filtered(
                    lambda l: l.product_id == variant and not getattr(l, 'is_reward_line', False))
                if not existing:
                    Line.create({'order_id': order.id, 'product_id': variant.id,
                                 'product_uom_qty': 1})
            # one-time discount coupon on the whole order (consumed on payment)
            cfg._issue_coupon(order, q['saved'])
            request.env['uellow.lamma.activity'].sudo().log('checkout', None, {
                'type': ltype, 'n': q['n'], 'subtotal': q['subtotal'],
                'saved': q['saved'], '_country': request.env.company.country_id.code or ''}, 'app')
            return _json({'ok': True, 'order_id': order.id})
        except Exception as e:
            _logger.exception('lamma app checkout failed: %s', e)
            return _json({'ok': False, 'error': 'server', 'detail': str(e)[:120]}, status=500)
