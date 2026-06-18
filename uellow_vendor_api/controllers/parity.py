# -*- coding: utf-8 -*-
"""Vendor app parity with the web portal — flash sales, promotions, stock,
restock, store style, and the capability matrix. /api/vendor/v1/*"""
from datetime import date, timedelta

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, img_url, bilingual, fmt_price,
)

# capability codes surfaced to the app (must match uellow.vendor.settings.cap_*)
CAP_CODES = [
    'add_products', 'edit_products', 'archive_products', 'update_stock',
    'publish_products', 'manage_price', 'flash_sale', 'bundles',
    'join_promotions', 'import_products', 'manage_orders', 'cancel_orders',
    'restock', 'edit_store', 'request_payout',
]


def _cap_guard(vendor, code):
    """Return a fail() Response when the vendor lacks capability `code`, else None."""
    if not vendor.cap(code):
        return fail('FORBIDDEN', 'This action is disabled for your account.',
                    status=403, capability=code)
    return None


class VendorParityAPI(http.Controller):

    # ───────────────────────── Capabilities ─────────────────────────
    @http.route('/api/vendor/v1/capabilities', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def capabilities(self, **kw):
        """The app calls this on login to show/hide features per vendor."""
        v = current_vendor()
        s = v.settings_id
        caps = {c: (bool(getattr(s, 'cap_' + c, True)) if s else True)
                for c in CAP_CODES}
        return ok({
            'capabilities': caps,
            'vendor_type': (s.vendor_type if s else 'seller'),
            'settlement_mode': (s.settlement_mode if s else 'wallet'),
            'hide_financials': bool(s.hide_financials) if s else False,
        })

    # ───────────────────────── Flash sales ──────────────────────────
    @http.route('/api/vendor/v1/flash-sales', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def flash_list(self, **kw):
        v = current_vendor()
        sales = request.env['uellow.flash.sale'].sudo().search(
            [('vendor_id', '=', v.id)], order='start_datetime desc', limit=50)
        out = []
        for s in sales:
            out.append({
                'id': s.id,
                'name': {'en': s.name or '', 'ar': s.name_ar or s.name or ''},
                'state': s.state,
                'discount_pct': s.discount_pct,
                'start': s.start_datetime and s.start_datetime.isoformat(),
                'end': s.end_datetime and s.end_datetime.isoformat(),
                'remaining_seconds': s.remaining_seconds,
                'units_sold': s.units_sold,
                'revenue': s.revenue,
                'product_count': len(s.product_ids),
            })
        return ok(out)

    @http.route('/api/vendor/v1/flash-sales', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def flash_create(self, **kw):
        v = current_vendor()
        guard = _cap_guard(v, 'flash_sale')
        if guard:
            return guard
        p = get_payload()
        try:
            pids = [int(x) for x in (p.get('product_ids') or []) if x]
        except (TypeError, ValueError):
            pids = []
        if not pids:
            return fail('VALIDATION', 'Select at least one product.')
        # vendor may only flash their OWN products
        Tmpl = request.env['product.template'].sudo()
        own = Tmpl.search([('id', 'in', pids), ('vendor_id', '=', v.id)]).ids
        if not own:
            return fail('VALIDATION', 'No eligible products.')
        sale = request.env['uellow.flash.sale'].sudo().create({
            'vendor_id': v.id,
            'name': p.get('name_en') or p.get('name') or 'Flash Sale',
            'name_ar': p.get('name_ar') or '',
            'discount_pct': float(p.get('discount_pct') or 0),
            'start_datetime': (p.get('start') or '').replace('T', ' ') or fields.Datetime.now(),
            'end_datetime': (p.get('end') or '').replace('T', ' ') or False,
            'product_ids': [(6, 0, own)],
        })
        return ok({'id': sale.id, 'state': sale.state})

    @http.route('/api/vendor/v1/flash-sales/<int:sale_id>/end', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def flash_end(self, sale_id, **kw):
        v = current_vendor()
        guard = _cap_guard(v, 'flash_sale')
        if guard:
            return guard
        sale = request.env['uellow.flash.sale'].sudo().browse(sale_id)
        if not sale.exists() or sale.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Flash sale not found', status=404)
        sale.action_end()
        return ok({'id': sale.id, 'state': sale.state})

    # ───────────────────────── Promotions ───────────────────────────
    @http.route('/api/vendor/v1/promotions', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def promo_list(self, **kw):
        v = current_vendor()
        Promo = request.env['mobile.app.promotion'].sudo()
        promos = Promo.search([
            ('state', 'in', ('open', 'running')),
            ('vendor_joinable', '=', True), ('active', '=', True),
        ], order='date_from')
        avail = [{
            'id': pr.id,
            'name': {'en': pr.name or '', 'ar': getattr(pr, 'name_ar', '') or pr.name or ''},
            'min_discount_pct': pr.min_discount_pct,
            'max_discount_pct': pr.max_discount_pct,
            'date_from': pr.date_from and str(pr.date_from),
            'date_to': pr.date_to and str(pr.date_to),
        } for pr in promos]
        Line = request.env['mobile.promotion.line'].sudo()
        mine = [{
            'id': ln.id,
            'promotion': ln.promotion_id.name,
            'product': ln.product_tmpl_id.name,
            'discount_pct': ln.discount_pct,
            'state': ln.state,
        } for ln in Line.search([('vendor_id', '=', v.id)],
                                order='create_date desc', limit=100)]
        return ok({'available': avail, 'mine': mine})

    @http.route('/api/vendor/v1/promotions/join', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def promo_join(self, **kw):
        v = current_vendor()
        guard = _cap_guard(v, 'join_promotions')
        if guard:
            return guard
        p = get_payload()
        Promo = request.env['mobile.app.promotion'].sudo()
        promo = Promo.browse(int(p.get('promotion_id') or 0))
        if not promo.exists() or promo.state not in ('open', 'running') \
                or not promo.vendor_joinable:
            return fail('VALIDATION', 'Promotion not joinable.')
        Line = request.env['mobile.promotion.line'].sudo()
        Tmpl = request.env['product.template'].sudo()
        # items: [{product_id, discount_pct}, ...]
        created = 0
        for it in (p.get('items') or []):
            try:
                pid = int(it.get('product_id'))
                pct = float(it.get('discount_pct') or 0)
            except (TypeError, ValueError):
                continue
            pct = max(promo.min_discount_pct, min(promo.max_discount_pct, pct))
            tmpl = Tmpl.browse(pid)
            if not tmpl.exists() or tmpl.vendor_id.id != v.id:
                continue
            if Line.search_count([('promotion_id', '=', promo.id),
                                  ('product_tmpl_id', '=', pid)]):
                continue
            Line.create({
                'promotion_id': promo.id, 'product_tmpl_id': pid,
                'vendor_id': v.id, 'discount_pct': pct, 'state': 'pending',
            })
            created += 1
        return ok({'joined': created})

    # ───────────────────────── Stock list ───────────────────────────
    @http.route('/api/vendor/v1/stock', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def stock_list(self, **kw):
        v = current_vendor()
        p = get_payload()
        flt = (p.get('filter') or 'all')          # all / low / out
        Tmpl = request.env['product.template'].sudo()
        prods = Tmpl.search([('vendor_id', '=', v.id), ('active', '=', True)],
                            order='name', limit=300)
        out = []
        for t in prods:
            qty = t.qty_available
            if flt == 'low' and not (0 < qty <= 5):
                continue
            if flt == 'out' and qty > 0:
                continue
            out.append({
                'id': t.id,
                'name': t.name,
                'image': img_url('product.template', t.id, 'image_128',
                                 unique=t.write_date),
                'sku': t.default_code or '',
                'qty': qty,
                'price': fmt_price(t.list_price),
                'low': 0 < qty <= 5,
                'out': qty <= 0,
            })
        return ok(out)

    # ───────────────────────── Restock requests ─────────────────────
    @http.route('/api/vendor/v1/restock', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def restock_list(self, **kw):
        v = current_vendor()
        VL = request.env['uellow.vendor.location'].sudo()
        vloc = VL.search([('partner_id', '=', v.partner_id.id)], limit=1)
        reqs = request.env['uellow.restock.request'].sudo().search(
            [('vendor_location_id', '=', vloc.id)] if vloc else [('id', '=', 0)],
            order='create_date desc', limit=80)
        out = [{
            'id': r.id,
            'state': r.state,
            'expected_date': r.expected_date and str(r.expected_date),
            'notes': r.notes or '',
            'lines': [{'product': l.product_id.display_name,
                       'qty': l.qty_requested} for l in r.line_ids],
            'date': r.create_date and r.create_date.isoformat(),
        } for r in reqs]
        return ok(out)

    @http.route('/api/vendor/v1/restock', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def restock_create(self, **kw):
        v = current_vendor()
        guard = _cap_guard(v, 'restock')
        if guard:
            return guard
        p = get_payload()
        try:
            pid = int(p.get('product_id'))
            qty = int(p.get('qty') or 0)
        except (TypeError, ValueError):
            return fail('VALIDATION', 'product_id and qty required.')
        if qty <= 0:
            return fail('VALIDATION', 'qty must be > 0.')
        VL = request.env['uellow.vendor.location'].sudo()
        vloc = VL.search([('partner_id', '=', v.partner_id.id)], limit=1)
        if not vloc:
            vloc = VL.create_for_vendor(v.partner_id)
        req = request.env['uellow.restock.request'].sudo().create({
            'vendor_location_id': vloc.id,
            'expected_date': date.today() + timedelta(days=7),
            'notes': p.get('notes') or '',
            'line_ids': [(0, 0, {'product_id': pid, 'qty_requested': qty})],
        })
        req.action_submit()
        return ok({'id': req.id, 'state': req.state})

    # ───────────────────────── Store style ──────────────────────────
    @http.route('/api/vendor/v1/style', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def style_get(self, **kw):
        v = current_vendor()
        s = v._ensure_settings()
        return ok({
            'brand_color': v.brand_color or '',
            'flash_bg_color': s.flash_bg_color or '',
            'flash_accent_color': s.flash_accent_color or '',
            'section_title_color': s.section_title_color or '',
            'price_color': s.price_color or '',
            'badge_color': s.badge_color or '',
            'header_text_color': s.header_text_color or '',
        })

    @http.route('/api/vendor/v1/style', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def style_save(self, **kw):
        v = current_vendor()
        guard = _cap_guard(v, 'edit_store')
        if guard:
            return guard
        p = get_payload()
        s = v._ensure_settings()
        vals = {}
        for f in ('flash_bg_color', 'flash_accent_color', 'section_title_color',
                  'price_color', 'badge_color', 'header_text_color'):
            if f in p:
                vals[f] = p.get(f) or False
        if vals:
            s.write(vals)
        if 'brand_color' in p:
            v.brand_color = p.get('brand_color') or False
        return ok({'saved': True})
