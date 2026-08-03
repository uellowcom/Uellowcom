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
