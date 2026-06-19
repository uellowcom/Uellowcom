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


_RESTOCK_STATES = {
    'draft':     {'en': 'Draft',                'ar': 'مسودة'},
    'submitted': {'en': 'Pending approval',     'ar': 'بانتظار الموافقة'},
    'approved':  {'en': 'Approved — to deliver','ar': 'موافق — بانتظار التسليم'},
    'received':  {'en': 'Received',             'ar': 'تم الاستلام'},
    'cancelled': {'en': 'Cancelled',           'ar': 'ملغي'},
}


def _ser_restock(r, detail=False):
    po = r.purchase_order_id
    cur = po.currency_id if po else r.partner_id.company_id.currency_id
    out = {
        'id': r.id, 'name': r.name, 'state': r.state,
        'state_label': _RESTOCK_STATES.get(r.state, {'en': r.state, 'ar': r.state}),
        'expected_date': r.expected_date and str(r.expected_date),
        'pickup_date': r.pickup_date and str(r.pickup_date),
        'confirmed_date': r.confirmed_date and str(r.confirmed_date),
        'transport_method': r.transport_method or '',
        'notes': r.notes or '',
        'location': r.location_id.complete_name if r.location_id else '',
        'total_units': r.total_units,
        'po_name': po.name if po else '',
        'po_total': fmt_price(po.amount_total, po.currency_id) if po else None,
        'has_handover': bool(po) and r.state in ('approved', 'received'),
        'date': r.create_date and r.create_date.isoformat(),
    }
    if detail:
        po_price = {l.product_id.id: l.price_unit for l in po.order_line} if po else {}
        out['lines'] = [{
            'product': l.product_id.display_name,
            'qty': l.qty_requested,
            'qty_received': l.qty_received,
            'qty_damaged': l.qty_damaged,
            'price': fmt_price(po_price.get(l.product_id.id, l.product_id.standard_price), cur),
        } for l in r.line_ids]
        # Timeline from the chatter.
        out['timeline'] = [{
            'body': (m.body or '').strip(),
            'author': m.author_id.name or 'System',
            'when': m.date.isoformat() if m.date else '',
        } for m in r.message_ids.sorted('id') if (m.body or '').strip()]
    return out


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

    @http.route('/api/vendor/v1/flash-sales/<int:sale_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def flash_detail(self, sale_id, **kw):
        """Full promotion record — openable after creation: header stats plus
        every product with its effective discount and resulting sale price."""
        v = current_vendor()
        s = request.env['uellow.flash.sale'].sudo().browse(sale_id)
        if not s.exists() or s.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Promotion not found', 404)
        cur = v.currency_id or request.env.company.currency_id
        products = []
        for pt in s.product_ids:
            pct = s._product_discount(pt)
            base = pt.list_price or 0.0
            products.append({
                'id': pt.id,
                'name': bilingual(pt, 'name'),
                'image_url': (img_url('product.template', pt.id, 'image_128',
                                      unique=pt.write_date) if pt.image_128 else None),
                'list_price': fmt_price(base, cur),
                'discount_pct': pct,
                'sale_price': fmt_price(base * (1 - pct / 100.0), cur),
            })
        return ok({
            'id': s.id,
            'name': {'en': s.name or '', 'ar': s.name_ar or s.name or ''},
            'state': s.state,
            'discount_pct': s.discount_pct,
            'extra_commission': s.extra_commission,
            'max_quantity': s.max_quantity,
            'start': s.start_datetime and s.start_datetime.isoformat(),
            'end': s.end_datetime and s.end_datetime.isoformat(),
            'remaining_seconds': s.remaining_seconds,
            'units_sold': s.units_sold,
            'revenue': fmt_price(s.revenue or 0, cur),
            'product_count': len(s.product_ids),
            'products': products,
        })

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
        Tmpl = request.env['product.template'].sudo()
        # Per-product lines [{product_id, discount_pct}] take priority; fall back
        # to a plain product_ids list with the general discount.
        raw_lines = p.get('lines') or []
        per_prod = {}
        if isinstance(raw_lines, list) and raw_lines:
            for ln in raw_lines:
                try:
                    per_prod[int(ln.get('product_id'))] = float(ln.get('discount_pct') or 0)
                except (TypeError, ValueError):
                    continue
            pids = list(per_prod.keys())
        else:
            try:
                pids = [int(x) for x in (p.get('product_ids') or []) if x]
            except (TypeError, ValueError):
                pids = []
        if not pids:
            return fail('VALIDATION', 'Select at least one product.')
        # vendor may only flash their OWN products
        own = Tmpl.search([('id', 'in', pids), ('vendor_id', '=', v.id)]).ids
        if not own:
            return fail('VALIDATION', 'No eligible products.')
        line_cmds = [(0, 0, {'product_id': pid, 'discount_pct': per_prod.get(pid, 0.0)})
                     for pid in own] if per_prod else []
        sale = request.env['uellow.flash.sale'].sudo().create({
            'vendor_id': v.id,
            'name': p.get('name_en') or p.get('name') or 'Flash Sale',
            'name_ar': p.get('name_ar') or '',
            'discount_pct': float(p.get('discount_pct') or 0),
            'start_datetime': (p.get('start') or '').replace('T', ' ') or fields.Datetime.now(),
            'end_datetime': (p.get('end') or '').replace('T', ' ') or False,
            'product_ids': [(6, 0, own)],
            'line_ids': line_cmds,
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
        return ok([_ser_restock(r) for r in reqs])

    @http.route('/api/vendor/v1/restock/<int:req_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def restock_detail(self, req_id, **kw):
        v = current_vendor()
        r = request.env['uellow.restock.request'].sudo().browse(req_id)
        if not r.exists() or r.partner_id.id != v.partner_id.id:
            return fail('NOT_FOUND', 'Request not found', status=404)
        return ok(_ser_restock(r, detail=True))

    @http.route('/api/vendor/v1/restock/<int:req_id>/handover', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def restock_handover(self, req_id, **kw):
        """Handover / delivery note PDF (the linked PO), available after approval."""
        v = current_vendor()
        r = request.env['uellow.restock.request'].sudo().browse(req_id)
        if not r.exists() or r.partner_id.id != v.partner_id.id:
            return fail('NOT_FOUND', 'Request not found', status=404)
        if r.state not in ('approved', 'received') or not r.purchase_order_id:
            return fail('NOT_READY', 'Available after approval.', status=409)
        try:
            from .orders import _pdf_attachment_url
            pdf, _t = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'uellow_documents.uellow_purchaseorder', [r.purchase_order_id.id])
            import base64 as _b64
            att = request.env['ir.attachment'].sudo().create({
                'name': 'handover-%s.pdf' % r.name, 'type': 'binary',
                'datas': _b64.b64encode(pdf), 'mimetype': 'application/pdf',
                'res_model': 'uellow.restock.request', 'res_id': r.id,
            })
            att.generate_access_token()
            base = request.httprequest.host_url.rstrip('/')
            url = '%s/web/content/%s?access_token=%s&download=true&filename=handover-%s.pdf' % (
                base, att.id, att.access_token, r.name)
        except Exception as e:
            return fail('REPORT_ERROR', str(e), status=500)
        return ok({'url': url})

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
        # Pickup/delivery date chosen by the vendor (defaults to +7 days).
        pickup = (p.get('pickup_date') or '').strip()
        try:
            from datetime import datetime as _dt
            pdate = _dt.strptime(pickup, '%Y-%m-%d').date() if pickup else (date.today() + timedelta(days=7))
        except ValueError:
            pdate = date.today() + timedelta(days=7)
        transport = p.get('transport_method')
        if transport not in ('self', 'carrier', 'uellow'):
            transport = 'self'
        req = request.env['uellow.restock.request'].sudo().create({
            'vendor_location_id': vloc.id,
            'expected_date': pdate,
            'pickup_date': pdate,
            'transport_method': transport,
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
