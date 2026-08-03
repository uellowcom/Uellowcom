# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from .main import _lines_from_ids


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
            'enabled': cfg.active,
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
