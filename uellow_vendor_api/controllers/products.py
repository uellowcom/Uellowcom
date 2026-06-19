# -*- coding: utf-8 -*-
"""Vendor products — /api/vendor/v1/products*"""
import base64
import binascii
import csv
import io
import json

from odoo import http, SUPERUSER_ID
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
        # Main template image, falling back to the first gallery image so the
        # card never shows blank when a product only has gallery images.
        'image_url': (
            img_url('product.template', t.id, 'image_256', unique=t.write_date)
            if t.image_256 else (
                img_url('product.image', t.product_template_image_ids[0].id,
                        'image_256', unique=t.product_template_image_ids[0].write_date)
                if t.product_template_image_ids else None)),
        'rejection_reason': t.vendor_rejection_reason or '',
        'sales_count': float(getattr(t, 'sales_count', 0) or 0),
        'active': bool(t.active),
        'under_review': bool(getattr(t, 'under_review', False)),
    }
    if detail:
        out['pending_change'] = (t.pending_change_id.change_summary or '') \
            if getattr(t, 'under_review', False) else ''
        out['description_sale'] = t.description_sale or ''
        out['description_sale_ar'] = t.with_context(lang='ar_001').description_sale or ''
        out['description_sale_en'] = t.with_context(lang='en_US').description_sale or ''
        out['description'] = t.description or ''
        out['default_code'] = t.default_code or ''
        out['barcode'] = t.barcode or ''
        out['weight'] = float(t.weight or 0)
        categ = t.public_categ_ids[:1]
        out['category'] = {'id': categ.id if categ else 0,
                           'name': bilingual(categ, 'name') if categ else {'en': '', 'ar': ''}}
        out['name_ar'] = t.with_context(lang='ar_001').name or ''
        out['name_en'] = t.with_context(lang='en_US').name or ''
        out['gallery'] = [
            img_url('product.image', im.id, 'image_256', unique=im.write_date)
            for im in t.product_template_image_ids]
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
        elif state == 'archived':
            domain += [('active', '=', False)]
        if search:
            domain += [('name', 'ilike', search)]
        Tmpl = request.env['product.template'].sudo()
        if state == 'archived':
            Tmpl = Tmpl.with_context(active_test=False)
        total = Tmpl.search_count(domain)
        rows = Tmpl.search(domain, order='write_date desc',
                            limit=per_page, offset=(page - 1) * per_page)
        return ok([_ser_tmpl(t) for t in rows], meta={
            'page': page, 'per_page': per_page, 'total': total,
            'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/vendor/v1/products/by-barcode', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def product_by_barcode(self, **kw):
        """Resolve a scanned barcode (or SKU) to one of the vendor's products."""
        v = current_vendor()
        code = (get_payload().get('barcode') or '').strip()
        if not code:
            return fail('NO_BARCODE', 'barcode required')
        Tmpl = request.env['product.template'].sudo().with_context(active_test=False)
        t = Tmpl.search(['&', ('vendor_id', '=', v.id),
                         '|', ('barcode', '=', code), ('default_code', '=', code)], limit=1)
        if not t:
            return fail('NOT_FOUND', 'No product matches this code', 404, barcode=code)
        return ok({'product': _ser_tmpl(t, detail=True)})

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

    @http.route('/api/vendor/v1/categories', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_categories(self, **kw):
        cats = request.env['product.public.category'].sudo().search(
            [], order='parent_id, sequence, name', limit=400)
        return ok([{
            'id': c.id,
            'name': bilingual(c, 'name'),
            'parent': c.parent_id.name or '',
        } for c in cats])

    @http.route('/api/vendor/v1/products/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_product(self, **kw):
        v = current_vendor()
        if not v.cap('add_products'):
            return fail('FORBIDDEN', 'Adding products is disabled for your account.', 403, capability='add_products')
        p = get_payload()
        name_en = (p.get('name_en') or p.get('name') or '').strip()
        name_ar = (p.get('name_ar') or '').strip()
        if not name_en and not name_ar:
            return fail('MISSING_NAME', 'Product name required')
        name = name_en or name_ar
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
        for f in ('standard_price', 'weight'):
            if f in p:
                try:
                    vals[f] = float(p[f])
                except (TypeError, ValueError):
                    pass
        if p.get('category_id'):
            try:
                vals['public_categ_ids'] = [(6, 0, [int(p['category_id'])])]
            except (TypeError, ValueError):
                pass
        gallery = [g for g in (p.get('gallery') or []) if g]
        main_b64 = p.get('image_base64') or (gallery[0] if gallery else None)
        if main_b64:
            try:
                raw = base64.b64decode(main_b64.split(',', 1)[-1])
                vals['image_1920'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        # product create touches stock.warehouse defaults → real superuser env.
        senv = request.env(user=SUPERUSER_ID)
        t = senv['product.template'].create(vals)
        # Arabic name translation
        if name_ar:
            try:
                t.with_context(lang='ar_001').write({'name': name_ar})
                if name_en:
                    t.with_context(lang='en_US').write({'name': name_en})
            except Exception:
                pass
        # Arabic description translation
        desc_ar = (p.get('description_sale_ar') or '').strip()
        if desc_ar:
            try:
                t.with_context(lang='ar_001').write({'description_sale': desc_ar})
            except Exception:
                pass
        # extra gallery images (skip the one already used as main)
        extra = gallery[1:] if (gallery and not p.get('image_base64')) else gallery
        for g in extra:
            try:
                raw = base64.b64decode(g.split(',', 1)[-1])
                senv['product.image'].create({
                    'product_tmpl_id': t.id,
                    'name': name,
                    'image_1920': base64.b64encode(raw),
                })
            except (binascii.Error, ValueError):
                continue
        return ok({'id': t.id, 'product': _ser_tmpl(t, detail=True)})

    @http.route('/api/vendor/v1/products/import', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def import_products(self, **kw):
        """Bulk-create products from CSV text. Columns (header row, any order):
        name_en, name_ar, sku, barcode, cost, price, category, description."""
        v = current_vendor()
        if not (v.cap('import_products') or v.cap('add_products')):
            return fail('FORBIDDEN', 'Importing products is disabled for your account.', 403, capability='import_products')
        text = (get_payload().get('csv') or '').strip()
        if not text:
            return fail('NO_CSV', 'csv text required')
        try:
            reader = csv.DictReader(io.StringIO(text))
        except Exception as e:
            return fail('BAD_CSV', 'Could not parse CSV: %s' % e)

        def num(x):
            try:
                return float(str(x).strip())
            except (TypeError, ValueError):
                return 0.0

        # product.template create touches stock.warehouse defaults that an
        # su-on-public env can't reach → use a genuine superuser env.
        senv = request.env(user=SUPERUSER_ID)
        Tmpl = senv['product.template']
        Cat = senv['product.public.category']
        created, errors = 0, []
        for i, row in enumerate(reader, start=2):  # row 1 = header
            row = {(k or '').strip().lower(): (val or '').strip()
                   for k, val in row.items()}
            name_en = row.get('name_en') or row.get('name') or ''
            name_ar = row.get('name_ar') or ''
            if not name_en and not name_ar:
                errors.append('Row %d: missing name' % i)
                continue
            vals = {
                'name': name_en or name_ar,
                'list_price': num(row.get('price')),
                'standard_price': num(row.get('cost')),
                'default_code': row.get('sku') or '',
                'barcode': row.get('barcode') or False,
                'description_sale': row.get('description') or '',
                'vendor_id': v.id,
                'vendor_approval_state': 'pending',
                'vendor_submitted_by': v.user_id.id,
                'is_published': False,
                'sale_ok': True, 'purchase_ok': False,
            }
            cat_name = row.get('category')
            if cat_name:
                cat = Cat.search([('name', 'ilike', cat_name)], limit=1)
                if cat:
                    vals['public_categ_ids'] = [(6, 0, [cat.id])]
            try:
                t = Tmpl.create(vals)
                if name_ar:
                    t.with_context(lang='ar_001').write({'name': name_ar})
                    if name_en:
                        t.with_context(lang='en_US').write({'name': name_en})
                created += 1
            except Exception as e:
                errors.append('Row %d: %s' % (i, e))
        return ok({'created': created, 'errors': errors[:20], 'error_count': len(errors)})

    @http.route('/api/vendor/v1/products/<int:pid>/update', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_product(self, pid, **kw):
        v = current_vendor()
        if not v.cap('edit_products'):
            return fail('FORBIDDEN', 'Editing products is disabled for your account.', 403, capability='edit_products')
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        p = get_payload()

        # Content/price edits → admin approval (live product keeps old values).
        proposed = {}
        for f in ('name', 'description_sale', 'default_code', 'barcode'):
            if f in p and (p[f] or '') != (t[f] or ''):
                proposed[f] = p[f]
        if 'list_price' in p and v.cap('manage_price'):
            try:
                np = float(p['list_price'])
                if np != (t.list_price or 0):
                    proposed['list_price'] = np
            except (TypeError, ValueError):
                pass
        if 'standard_price' in p and v.cap('manage_price'):
            try:
                nc = float(p['standard_price'])
                if nc != (t.standard_price or 0):
                    proposed['standard_price'] = nc
            except (TypeError, ValueError):
                pass
        if 'weight' in p:
            try:
                nw = float(p['weight'])
                if nw != (t.weight or 0):
                    proposed['weight'] = nw
            except (TypeError, ValueError):
                pass
        # Arabic name (translation) — special key applied on approval.
        if 'name_ar' in p:
            cur_ar = t.with_context(lang='ar_001').name or ''
            if (p['name_ar'] or '') != cur_ar:
                proposed['__name_ar'] = p['name_ar']
        # Arabic description (translation) — special key applied on approval.
        if 'description_sale_ar' in p:
            cur_d_ar = t.with_context(lang='ar_001').description_sale or ''
            if (p['description_sale_ar'] or '') != cur_d_ar:
                proposed['__desc_ar'] = p['description_sale_ar']
        # Storefront category — special key applied on approval.
        if p.get('category_id'):
            try:
                cid = int(p['category_id'])
                if cid not in t.public_categ_ids.ids:
                    proposed['__public_categ_id'] = cid
            except (TypeError, ValueError):
                pass
        if p.get('image_base64'):
            try:
                raw = base64.b64decode(p['image_base64'].split(',', 1)[-1])
                proposed['image_1920'] = base64.b64encode(raw).decode()
            except (binascii.Error, ValueError):
                pass
        # New gallery images — special key applied on approval.
        gallery = [g for g in (p.get('gallery') or []) if g]
        if gallery:
            proposed['__gallery'] = gallery

        # Operational toggles apply immediately (not content).
        if 'is_published' in p and v.cap('publish_products'):
            t.sudo().write({'is_published': bool(p['is_published'])})

        review = False
        if proposed:
            request.env['uellow.product.change'].sudo().submit_change(t, proposed, v.user_id)
            review = True
        return ok({'product': _ser_tmpl(t, detail=True), 'under_review': review})

    @http.route('/api/vendor/v1/products/<int:pid>/stock', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_stock(self, pid, **kw):
        v = current_vendor()
        if not v.cap('update_stock'):
            return fail('FORBIDDEN', 'Updating stock is disabled for your account.', 403, capability='update_stock')
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
        if not v.cap('archive_products'):
            return fail('FORBIDDEN', 'Archiving products is disabled for your account.', 403, capability='archive_products')
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        # Soft delete — unpublish + archive, never hard delete (refs in orders).
        t.sudo().write({'is_published': False, 'active': False})
        return ok({'archived': True})

    @http.route('/api/vendor/v1/products/<int:pid>/restore', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def restore_product(self, pid, **kw):
        v = current_vendor()
        if not v.cap('archive_products'):
            return fail('FORBIDDEN', 'Restoring products is disabled for your account.', 403, capability='archive_products')
        # Archived (active=False) records need active_test disabled to be found.
        t = request.env['product.template'].sudo().with_context(active_test=False).browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        # Un-archive only; stays unpublished until the vendor re-publishes.
        t.sudo().write({'active': True})
        return ok({'restored': True, 'product': _ser_tmpl(t, detail=True)})
