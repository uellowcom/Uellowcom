# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


def _lines_from_ids(ids):
    """Return (templates, engine-lines) for a list of product.template ids,
    preserving the given order and dropping missing/unpublished ones."""
    prods = request.env['product.template'].sudo().browse([int(i) for i in ids]).exists()
    prods = prods.filtered(lambda p: p.sale_ok)
    lines = [{'price': p.list_price or 0.0, 'cost': p.standard_price or 0.0} for p in prods]
    return prods, lines


def lamma_summary():
    """Compute the current session Lamma (used by web routes)."""
    ids = request.session.get('lamma_ids') or []
    ltype = request.session.get('lamma_type') or 'normal'
    cfg = request.env['uellow.lamma.config'].sudo().get_config()
    prods, lines = _lines_from_ids(ids)
    q = cfg.compute_lamma(lines, ltype)
    q['items'] = [{
        'id': p.id, 'name': p.name or '',
        'price': round(p.list_price or 0.0, 3),
        'url': p.website_url or ('/shop/%s' % p.id),
        'image': '/web/image/product.template/%s/image_256' % p.id,
    } for p in prods]
    q['label'] = cfg.brand_label
    q['badge'] = cfg.badge_text
    q['enabled'] = cfg.active and cfg.enable_all_products
    q['replace_add_to_cart'] = cfg.replace_add_to_cart
    q['min_items'] = cfg.min_items
    q['installment_enabled'] = cfg.installment_enabled
    q['installment_min_amount'] = cfg.installment_min_amount
    q['currency'] = (request.env.company.currency_id.symbol
                     or request.env.company.currency_id.name or 'KD')
    return q


class LammaWeb(http.Controller):
    """Session-based Lamma cart for the web storefront. New JSON routes only —
    nothing here overrides core cart/checkout behaviour."""

    @http.route('/lamma/get', type='json', auth='public', website=True)
    def get(self, **kw):
        return lamma_summary()

    @http.route('/lamma/add', type='json', auth='public', website=True)
    def add(self, product_id, lamma_type=None, **kw):
        ids = list(request.session.get('lamma_ids') or [])
        pid = int(product_id)
        if pid not in ids:
            ids.append(pid)
        request.session['lamma_ids'] = ids
        if lamma_type in ('normal', 'installment'):
            request.session['lamma_type'] = lamma_type
        return lamma_summary()

    @http.route('/lamma/remove', type='json', auth='public', website=True)
    def remove(self, product_id, **kw):
        ids = list(request.session.get('lamma_ids') or [])
        pid = int(product_id)
        if pid in ids:
            ids.remove(pid)
        request.session['lamma_ids'] = ids
        return lamma_summary()

    @http.route('/lamma/type', type='json', auth='public', website=True)
    def set_type(self, lamma_type, **kw):
        request.session['lamma_type'] = 'installment' if lamma_type == 'installment' else 'normal'
        return lamma_summary()

    @http.route('/lamma/clear', type='json', auth='public', website=True)
    def clear(self, **kw):
        request.session['lamma_ids'] = []
        return lamma_summary()

    @http.route('/lamma/checkout', type='json', auth='public', website=True)
    def checkout(self, **kw):
        """Turn the session Lamma into cart lines with the server-recomputed,
        margin-protected discount applied per line (native sale.order.line.discount).
        The price is re-derived here — the client value is never trusted."""
        ids = request.session.get('lamma_ids') or []
        ltype = request.session.get('lamma_type') or 'normal'
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        prods, lines = _lines_from_ids(ids)
        if len(prods) < max(1, cfg.min_items):
            return {'error': 'need_more', 'min_items': cfg.min_items}
        q = cfg.compute_lamma(lines, ltype)
        pct = q['discount_pct']
        order = request.website.sale_get_order(force_create=True)
        for p in prods:
            variant = p.product_variant_id
            if not variant:
                continue
            res = order._cart_update(product_id=variant.id, add_qty=1)
            line = request.env['sale.order.line'].sudo().browse(res.get('line_id'))
            if line.exists():
                line.write({'discount': pct, 'is_lamma': True, 'lamma_type': ltype})
        request.session['lamma_ids'] = []
        return {'redirect': '/shop/cart'}
