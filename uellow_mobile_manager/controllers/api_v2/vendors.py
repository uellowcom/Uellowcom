"""Vendor (multi-vendor) endpoints — /api/mobile/v2/vendors/*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, get_lang, paginate,
    img_url, bilingual,
)
from .products import serialize_product_card, _domain_published_for_app


def serialize_vendor_card(vendor, lang='en_US'):
    if not vendor:
        return None
    return {
        'id': vendor.id,
        'name': {
            'en': vendor.store_name_en or vendor.display_name or '',
            'ar': vendor.store_name_ar or vendor.store_name_en or vendor.display_name or '',
        },
        'slug': vendor.store_slug or f'v-{vendor.id}',
        'tagline': {
            'en': vendor.store_tagline_en or '',
            'ar': vendor.store_tagline_ar or vendor.store_tagline_en or '',
        },
        'logo':   img_url('uellow.vendor', vendor.id, 'logo_image',
                          unique=vendor.write_date) if 'logo_image' in vendor._fields else None,
        'banner': img_url('uellow.vendor', vendor.id, 'banner_image',
                          unique=vendor.write_date) if 'banner_image' in vendor._fields else None,
        'brand_color': vendor.brand_color or '#F5C320',
        'tier':        vendor.tier or 'standard',
        'country':     vendor.country_id.code if vendor.country_id else None,
        'product_count': _vendor_product_count(vendor),
        'order_count':   int(vendor.order_count or 0),
        'rating':        _vendor_rating(vendor),
    }


def _vendor_product_count(vendor):
    try:
        return request.env['product.template'].sudo().search_count([
            ('vendor_id', '=', vendor.id), ('is_published', '=', True),
        ])
    except Exception:
        return 0


def _vendor_rating(vendor):
    """Average rating across all the vendor's products. Cached briefly
    in a session field so we don't recompute on every list call."""
    try:
        recs = request.env['product.template'].sudo().search(
            [('vendor_id', '=', vendor.id), ('is_published', '=', True)],
            limit=200,
        )
        if not recs:
            return {'avg': 0, 'count': 0}
        totals = [(p.rating_avg or 0, p.rating_count or 0)
                  for p in recs if (p.rating_count or 0) > 0]
        if not totals:
            return {'avg': 0, 'count': 0}
        n = sum(c for _, c in totals)
        s = sum(a * c for a, c in totals)
        return {'avg': round(s / max(n, 1), 1), 'count': n}
    except Exception:
        return {'avg': 0, 'count': 0}


class MobileVendorsAPI(http.Controller):

    @http.route('/api/mobile/v2/vendors', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_vendors(self, **kw):
        lang = get_lang()
        p = get_payload()
        Vendor = request.env.get('uellow.vendor')
        if Vendor is None:
            return ok([])
        domain = []
        if 'state' in Vendor._fields:
            domain.append(('state', 'in', ['approved', 'active']))
        q = (p.get('q') or '').strip()
        if q:
            domain += ['|', ('store_name_en', 'ilike', q),
                            ('store_name_ar', 'ilike', q)]
        recs = Vendor.sudo().search(domain, order='order_count desc, id desc')
        items, meta = paginate(
            recs, page=p.get('page', 1), per_page=p.get('per_page', 24),
            serializer=lambda v: serialize_vendor_card(v, lang),
        )
        return ok(items, meta)

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def vendor_detail(self, vendor_id, **kw):
        lang = get_lang()
        Vendor = request.env.get('uellow.vendor')
        if Vendor is None:
            return fail('UNAVAILABLE', 'Vendor module not installed', 503)
        vendor = Vendor.sudo().browse(vendor_id)
        if not vendor.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        card = serialize_vendor_card(vendor, lang)
        about = {
            'en': getattr(vendor, 'store_about_en', '') or '',
            'ar': getattr(vendor, 'store_about_ar', '') or '',
        }
        return ok({
            **card,
            'about':       about,
            'sla_hours':   vendor.sla_hours or 0,
            'phone':       vendor.contact_phone or '',
            'business_name': vendor.business_name or '',
            'categories':  _vendor_category_breakdown(vendor),
        })

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def vendor_products(self, vendor_id, **kw):
        lang = get_lang()
        p = get_payload()
        domain = _domain_published_for_app() + [('vendor_id', '=', vendor_id)]
        sort = {
            'newest':     'create_date desc',
            'price_asc':  'list_price asc',
            'price_desc': 'list_price desc',
            'top_rated':  'rating_avg desc' if 'rating_avg' in request.env['product.template']._fields else 'create_date desc',
        }.get(p.get('sort', 'newest'), 'create_date desc')
        recs = request.env['product.template'].sudo().search(domain, order=sort)
        items, meta = paginate(
            recs, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )
        return ok(items, meta)


def _vendor_category_breakdown(vendor):
    """Top public categories this vendor sells in — useful for the
    vendor page's mini-nav."""
    recs = request.env['product.template'].sudo().search(
        [('vendor_id', '=', vendor.id), ('is_published', '=', True)],
        limit=300,
    )
    counts = {}
    for p in recs:
        for c in p.public_categ_ids:
            counts[c.id] = counts.get(c.id, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    cats = request.env['product.public.category'].sudo().browse([cid for cid, _ in top])
    by_id = {c.id: c for c in cats}
    return [{
        'id': cid,
        'name': bilingual(by_id[cid], 'name'),
        'count': cnt,
    } for cid, cnt in top if cid in by_id]
