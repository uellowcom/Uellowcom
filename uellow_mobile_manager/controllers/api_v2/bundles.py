"""Bundles — /api/mobile/v2/bundles[/<id>]

Read-only listing of published, available bundles for the app's bundle
feeds and the "bundles" block source. Each item is the bundle payload
PLUS the sellable product card (so the app can render the bundle exactly
like a product and add it to the cart in one tap).
"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail, get_lang, paginate
from .products import serialize_product_card, serialize_product_full


def _current_website_id():
    try:
        from ._common import get_website
        w = get_website()
        return w.id if w else None
    except Exception:
        return None


class MobileBundlesAPI(http.Controller):

    @http.route('/api/mobile/v2/bundles', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def bundles(self, **kw):
        p = get_payload()
        lang = get_lang()
        Bundle = request.env.get('uellow.bundle')
        if Bundle is None:
            return ok({'items': []})
        wid = _current_website_id()
        recs = Bundle.sudo().search(
            [('state', '=', 'published'),
             ('product_tmpl_id', '!=', False)],
            order='sequence, id desc')
        out = []
        for b in recs:
            # v2.2.21 — 'hide' bundles drop when unavailable; 'badge'/'sell'
            # stay listed and the card carries the state.
            if b._listing_state() == 'hidden':
                continue
            if b.website_ids and wid and wid not in b.website_ids.ids:
                continue
            data = b.to_mobile_dict(lang, with_components=True)
            card = serialize_product_card(b.product_tmpl_id, lang)
            if card:
                card['bundle_meta'] = b.to_mobile_dict(
                    lang, with_components=False)
                data['card'] = card
            out.append(data)
        # v2.2.24 — bundle-level filters for the Bundles screen filter bar.
        def _f(key):
            try:
                return float(p.get(key) or 0)
            except Exception:
                return 0.0
        mn, mx = _f('min_price'), _f('max_price')
        msave, mitems = _f('min_savings'), int(_f('min_items'))
        if mn > 0:
            out = [b for b in out if (b.get('price') or 0) >= mn]
        if mx > 0:
            out = [b for b in out if (b.get('price') or 0) <= mx]
        if msave > 0:
            out = [b for b in out if (b.get('savings_pct') or 0) >= msave]
        if mitems > 0:
            out = [b for b in out if (b.get('component_count') or 0) >= mitems]
        # v2.2.23 — sort for the Bundles screen filter chips.
        sort = (p.get('sort') or 'featured').strip()
        if sort == 'savings':
            out.sort(key=lambda x: -(x.get('savings_pct') or 0))
        elif sort == 'price_asc':
            out.sort(key=lambda x: x.get('price') or 0)
        elif sort == 'price_desc':
            out.sort(key=lambda x: -(x.get('price') or 0))
        elif sort == 'items':
            out.sort(key=lambda x: -(x.get('component_count') or 0))
        # 'featured' keeps the sequence order from search
        items, meta = paginate(
            out, page=p.get('page', 1), per_page=p.get('per_page', 12),
            serializer=lambda x: x)
        return ok({'items': items}, meta)

    @http.route('/api/mobile/v2/bundles/<int:bid>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def bundle_detail(self, bid, **kw):
        lang = get_lang()
        Bundle = request.env.get('uellow.bundle')
        if Bundle is None:
            return fail('NOT_FOUND', 'Bundles not available', 404)
        b = Bundle.sudo().browse(bid)
        if not b.exists() or b.state != 'published':
            return fail('NOT_FOUND', 'Bundle not found', 404)
        data = b.to_mobile_dict(lang, with_components=True)
        if b.product_tmpl_id:
            data['product'] = serialize_product_full(
                b.product_tmpl_id, lang)
        return ok(data)
