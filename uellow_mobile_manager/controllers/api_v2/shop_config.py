# -*- coding: utf-8 -*-
"""
Shop page config + brands (v2.1.57)
===================================
GET /api/mobile/v2/shop/config — section toggles + the "For You"
    hand-picked categories/brands (Mobile App ▸ Settings).
GET /api/mobile/v2/brands — top brand attribute values (with logo from
    product.brand when one matches by name) for the shop brands row.
"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, get_website, img_url, bilingual


def _brand_dict(value, Brand, Tmpl, base_dom):
    logo = None
    if Brand is not None:
        b = Brand.search([('name', '=ilike', value.name)], limit=1) \
            or Brand.search([('name', 'ilike', value.name)], limit=1)
        if b and getattr(b, 'image_1024', False):
            logo = img_url('product.brand', b.id, 'image_1024',
                           unique=b.write_date)
    n = Tmpl.search_count(
        base_dom + [('attribute_line_ids.value_ids', 'in', [value.id])])
    return {'value_id': value.id, 'name': value.name,
            'image': logo, 'product_count': n}


def _get_setting():
    Setting = request.env['mobile.app.setting'].sudo()
    wid = None
    try:
        wid = get_website().id
    except Exception:
        pass
    rec = None
    if wid:
        rec = Setting.search([('website_id', '=', wid)], limit=1)
    if not rec:
        rec = Setting.search([], limit=1)
    return rec


class MobileShopConfigAPI(http.Controller):

    @http.route('/api/mobile/v2/shop/config', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def shop_config(self, **kw):
        s = _get_setting()
        Tmpl = request.env['product.template'].sudo()
        base_dom = [('is_published', '=', True)]
        Brand = None
        if 'product.brand' in request.env:
            Brand = request.env['product.brand'].sudo()

        foryou_cats = []
        foryou_brands = []
        if s and getattr(s, 'shop_foryou_enabled', False):
            for c in s.shop_foryou_categ_ids:
                foryou_cats.append({
                    'id': c.id,
                    'name': bilingual(c, 'name'),
                    'image': img_url('product.public.category', c.id,
                                     'image_1920', unique=c.write_date)
                             if c.image_1920 else None,
                    'product_count': len(c.product_tmpl_ids),
                })
            for v in s.shop_foryou_brand_value_ids:
                foryou_brands.append(_brand_dict(v, Brand, Tmpl, base_dom))

        return ok({
            'show_recent': bool(getattr(s, 'shop_show_recent', True))
                           if s else True,
            'show_products': bool(getattr(s, 'shop_show_products', True))
                             if s else True,
            'show_brands': bool(getattr(s, 'shop_show_brands', True))
                           if s else True,
            'foryou_enabled': bool(getattr(s, 'shop_foryou_enabled', False))
                              if s else False,
            'foryou': {
                'categories': foryou_cats,
                'brands': foryou_brands,
            },
        })

    @http.route('/api/mobile/v2/brands', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def brands(self, **kw):
        """Top brand attribute values by product count.
        v2.1.59 — optional ?category_id= filter + bigger limit for the
        dedicated Brands screen."""
        from ._common import get_payload
        p = get_payload()
        cat_id = 0
        try:
            cat_id = int(p.get('category_id') or 0)
        except Exception:
            pass
        Val = request.env['product.attribute.value'].sudo()
        vals = Val.search([
            '|', '|',
            ('attribute_id.name', 'ilike', 'brand'),
            ('attribute_id.name', 'ilike', 'ماركة'),
            ('attribute_id.name', 'ilike', 'علامة'),
        ], limit=120)
        Tmpl = request.env['product.template'].sudo()
        base_dom = [('is_published', '=', True)]
        if cat_id:
            base_dom.append(('public_categ_ids', 'child_of', cat_id))
        Brand = None
        if 'product.brand' in request.env:
            Brand = request.env['product.brand'].sudo()
        out = []
        seen = set()
        for v in vals:
            key = (v.name or '').strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            d = _brand_dict(v, Brand, Tmpl, base_dom)
            if d['product_count'] > 0:
                out.append(d)
        out.sort(key=lambda d: -d['product_count'])
        return ok({'brands': out[:60]})
