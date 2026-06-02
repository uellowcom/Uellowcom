# -*- coding: utf-8 -*-
"""Vendor products — /api/vendor/v1/products*"""
import base64
import binascii

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price, bilingual, img_url,
)


def _ser_tmpl(t, detail=False):
    cur = t.currency_id or t.company_id.currency_id or request.env.company.currency_id
    out = {
        'id': t.id,
        'name': bilingual(t, 'name'),
        'list_price': fmt_price(t.list_price or 0, cur),
        'standard_price': fmt_price(t.standard_price or 0, cur),
        'is_published': bool(t.is_published),
        'qty_available': float(t.qty_available or 0),
        'approval_state': t.vendor_approval_state or 'draft',
        'image_url': img_url('product.template', t.id, 'image_256',
                             unique=t.write_date) if t.image_1920 else None,
        'rejection_reason': t.vendor_rejection_reason or '',
        'sales_count': float(getattr(t, 'sales_count', 0) or 0),
    }
    if detail:
        out['description_sale'] = t.description_sale or ''
        out['description'] = t.description or ''
        out['default_code'] = t.default_code or ''
        out['barcode'] = t.barcode or ''
        out['weight'] = float(t.weight or 0)
        out['variant_ids'] = [{
            'id': v.id,
            'name': v.display_name,
            'price': fmt_price(v.lst_price, cur),
            'qty':   float(v.qty_available or 0),
            'default_code': v.default_code or '',
        } for v in t.product_variant_ids]
    return out


class VendorProductsAPI(http.Controller):

    @http.route('/api/vendor/v1/products', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_products(self, **kw):
        v = current_vendor()
        p = get_payload()
        state = (p.get('state') or '').strip()
        search = (p.get('search') or '').strip()
        try:
            page = max(1, int(p.get('page') or 1))
            per_page = min(50, max(5, int(p.get('per_page') or 20)))
        except (TypeError, ValueError):
            page, per_page = 1, 20
        domain = [('vendor_id', '=', v.id)]
        if state == 'live':
            domain += [('vendor_approval_state', '=', 'approved'),
                        ('is_published', '=', True)]
        elif state == 'pending':
            domain += [('vendor_approval_state', 'in', ('draft', 'pending'))]
        elif state == 'rejected':
            domain += [('vendor_approval_state', '=', 'rejected')]
        elif state == 'low_stock':
            domain += [('qty_available', '<=', 5)]
        elif state == 'unpublished':
            domain += [('is_published', '=', False)]
        if search:
            domain += [('name', 'ilike', search)]
        Tmpl = request.env['product.template'].sudo()
        total = Tmpl.search_count(domain)
        rows = Tmpl.search(domain, order='write_date desc',
                            limit=per_page, offset=(page - 1) * per_page)
        return ok([_ser_tmpl(t) for t in rows], meta={
            'page': page, 'per_page': per_page, 'total': total,
            'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/vendor/v1/products/<int:pid>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def product_detail(self, pid, **kw):
        v = current_vendor()
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        return ok({'product': _ser_tmpl(t, detail=True)})

    @http.route('/api/vendor/v1/products/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_product(self, **kw):
        v = current_vendor()
        p = get_payload()
        name = (p.get('name') or '').strip()
        if not name:
            return fail('MISSING_NAME', 'Product name required')
        try:
            list_price = float(p.get('list_price') or 0)
        except (TypeError, ValueError):
            list_price = 0.0
        vals = {
            'name':              name,
            'list_price':        list_price,
            'vendor_id':         v.id,
            'vendor_approval_state': 'pending',
            'vendor_submitted_by': v.user_id.id,
            'is_published':      False,  # locked until approval
            'sale_ok':           True,
            'purchase_ok':       False,
            'description_sale':  (p.get('description_sale') or '').strip(),
            'default_code':      (p.get('default_code') or '').strip(),
            'barcode':           (p.get('barcode') or '').strip() or False,
        }
        if p.get('image_base64'):
            try:
                raw = base64.b64decode(p['image_base64'].split(',', 1)[-1])
                vals['image_1920'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        t = request.env['product.template'].sudo().create(vals)
        return ok({'id': t.id, 'product': _ser_tmpl(t, detail=True)})

    @http.route('/api/vendor/v1/products/<int:pid>/update', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_product(self, pid, **kw):
        v = current_vendor()
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        p = get_payload()
        vals = {}
        for f in ('name', 'description_sale', 'default_code', 'barcode'):
            if f in p:
                vals[f] = p[f]
        if 'list_price' in p:
            try: vals['list_price'] = float(p['list_price'])
            except (TypeError, ValueError): pass
        if 'is_published' in p:
            vals['is_published'] = bool(p['is_published'])
        if p.get('image_base64'):
            try:
                raw = base64.b64decode(p['image_base64'].split(',', 1)[-1])
                vals['image_1920'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        if vals:
            t.sudo().write(vals)
        return ok({'product': _ser_tmpl(t, detail=True)})

    @http.route('/api/vendor/v1/products/<int:pid>/stock', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_stock(self, pid, **kw):
        v = current_vendor()
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        p = get_payload()
        try:
            qty = float(p.get('qty') or 0)
        except (TypeError, ValueError):
            return fail('BAD_QTY', 'qty must be a number')
        product = t.product_variant_id
        loc = request.env['stock.location'].sudo().search(
            [('usage', '=', 'internal')], limit=1)
        if not product or not loc:
            return fail('NO_PRODUCT', 'No stockable variant', 400)
        # Use stock.quant update (the official path)
        request.env['stock.quant'].sudo().with_context(inventory_mode=True)._update_available_quantity(
            product, loc, qty - product.qty_available)
        return ok({'qty_available': float(t.qty_available or 0)})

    @http.route('/api/vendor/v1/products/<int:pid>/delete', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_product(self, pid, **kw):
        v = current_vendor()
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        # Soft delete — unpublish + archive, never hard delete (refs in orders).
        t.sudo().write({'is_published': False, 'active': False})
        return ok({'archived': True})
