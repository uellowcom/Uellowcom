# -*- coding: utf-8 -*-
"""Marketplace ADMIN mode — /api/vendor/v1/admin/*

A marketplace-admin user (no vendor record, in group_marketplace_manager or
base.group_system) logs into the same vendor app and gets a read/manage view
of the whole marketplace: all orders, vendors + their settings, module stats,
and the approval queue. Mirrors the uellow_multivendor backend.
"""
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_admin,
    fmt_price, bilingual, img_url,
)

CONFIRMED = ('sale', 'done')


def _sum_count(Order, domain):
    """(sum amount_total, count) for a domain, via read_group."""
    rg = Order.read_group(domain, ['amount_total:sum'], [])
    if rg:
        return rg[0].get('amount_total') or 0.0, rg[0].get('__count') or 0
    return 0.0, 0


class VendorAdminAPI(http.Controller):

    # ───────────────────────── dashboard ────────────────────────────
    @http.route('/api/vendor/v1/admin/dashboard', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_dashboard(self, **kw):
        env = request.env
        Order = env['sale.order'].sudo()
        cur = env.company.currency_id
        now = datetime.now()
        day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week0 = day0 - timedelta(days=day0.weekday())
        month0 = day0.replace(day=1)

        def gmv(since):
            s, _c = _sum_count(Order, [('state', 'in', CONFIRMED),
                                       ('date_order', '>=', since.strftime('%Y-%m-%d %H:%M:%S'))])
            return s

        gmv_today = gmv(day0)
        gmv_week = gmv(week0)
        gmv_month = gmv(month0)
        _t, orders_today = _sum_count(Order, [('state', 'in', CONFIRMED),
            ('date_order', '>=', day0.strftime('%Y-%m-%d %H:%M:%S'))])

        new_orders = Order.search_count([('state', '=', 'sent')])
        processing = Order.search_count([('state', '=', 'sale'),
                                         ('invoice_status', '!=', 'invoiced')])
        completed = Order.search_count([('invoice_status', '=', 'invoiced')])
        cancelled = Order.search_count([('state', '=', 'cancel')])

        Vendor = env['uellow.vendor'].sudo()
        active_vendors = Vendor.search_count([('state', '=', 'active')])
        pending_vendors = Vendor.search_count([('state', 'in', ('draft', 'pending'))])

        Tmpl = env['product.template'].sudo()
        pending_products = Tmpl.search_count([('vendor_id', '!=', False),
                                              ('vendor_approval_state', '=', 'pending')])
        pending_changes = env['uellow.product.change'].sudo().search_count(
            [('state', '=', 'pending')])

        commission_month = 0.0
        try:
            Comm = env['uellow.vendor.commission'].sudo()
            rg = Comm.read_group(
                [('create_date', '>=', month0.strftime('%Y-%m-%d %H:%M:%S'))],
                ['commission_amount:sum'], [])
            commission_month = (rg[0].get('commission_amount') if rg else 0.0) or 0.0
        except Exception:
            commission_month = 0.0

        # top vendors this month by GMV
        top = []
        try:
            rg = Order.read_group(
                [('state', 'in', CONFIRMED), ('vendor_id', '!=', False),
                 ('date_order', '>=', month0.strftime('%Y-%m-%d %H:%M:%S'))],
                ['amount_total:sum'], ['vendor_id'],
                orderby='amount_total desc', limit=5)
            for r in rg:
                vid = r['vendor_id'][0] if r.get('vendor_id') else 0
                top.append({'id': vid,
                            'name': r['vendor_id'][1] if r.get('vendor_id') else '',
                            'gmv': fmt_price(r.get('amount_total') or 0, cur)})
        except Exception:
            top = []

        # GMV by vendor type (this month) — bucket per-vendor GMV by type
        by_type = {}
        try:
            rg = Order.read_group(
                [('state', 'in', CONFIRMED), ('vendor_id', '!=', False),
                 ('date_order', '>=', month0.strftime('%Y-%m-%d %H:%M:%S'))],
                ['amount_total:sum'], ['vendor_id'])
            vids = [r['vendor_id'][0] for r in rg if r.get('vendor_id')]
            vtype = {vv.id: (vv.vendor_type or 'seller')
                     for vv in env['uellow.vendor'].sudo().browse(vids)}
            for r in rg:
                vid = r['vendor_id'][0] if r.get('vendor_id') else 0
                t = vtype.get(vid, 'seller')
                by_type[t] = by_type.get(t, 0.0) + (r.get('amount_total') or 0.0)
        except Exception:
            by_type = {}
        by_type_out = [{'type': k, 'gmv': fmt_price(val, cur)}
                       for k, val in sorted(by_type.items(), key=lambda x: -x[1])]

        return ok({
            'gmv': {'today': fmt_price(gmv_today, cur),
                    'week': fmt_price(gmv_week, cur),
                    'month': fmt_price(gmv_month, cur)},
            'by_type': by_type_out,
            'orders': {'today': orders_today, 'new': new_orders,
                       'processing': processing, 'completed': completed,
                       'cancelled': cancelled},
            'vendors': {'active': active_vendors, 'pending': pending_vendors},
            'approvals': {'products': pending_products, 'edits': pending_changes},
            'commission_month': fmt_price(commission_month, cur),
            'top_vendors': top,
        })

    # ───────────────────────── all orders ───────────────────────────
    @http.route('/api/vendor/v1/admin/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_orders(self, **kw):
        env = request.env
        p = get_payload()
        state = (p.get('state') or '').strip()
        search = (p.get('search') or '').strip()
        try:
            page = max(1, int(p.get('page') or 1))
            per_page = min(50, max(5, int(p.get('per_page') or 20)))
        except (TypeError, ValueError):
            page, per_page = 1, 20
        domain = [('vendor_id', '!=', False)]
        if state == 'new':         domain += [('state', '=', 'sent')]
        elif state == 'processing': domain += [('state', '=', 'sale'),
                                               ('invoice_status', '!=', 'invoiced')]
        elif state == 'completed': domain += [('invoice_status', '=', 'invoiced')]
        elif state == 'cancelled': domain += [('state', '=', 'cancel')]
        if search:
            domain += ['|', ('name', 'ilike', search),
                            ('partner_id.name', 'ilike', search)]
        Order = env['sale.order'].sudo()
        total = Order.search_count(domain)
        rows = Order.search(domain, order='id desc',
                            limit=per_page, offset=(page - 1) * per_page)
        out = []
        for o in rows:
            out.append({
                'id': o.id, 'name': o.name, 'state': o.state,
                'when': (o.date_order or o.create_date).isoformat()
                        if (o.date_order or o.create_date) else '',
                'vendor': o.vendor_id.display_name or '',
                'customer': o.partner_id.name or '',
                'amount': fmt_price(o.amount_total, o.currency_id),
                'invoice_status': o.invoice_status,
            })
        return ok(out, meta={'page': page, 'per_page': per_page, 'total': total,
                             'pages': (total + per_page - 1) // per_page})

    # ───────────────────────── vendors ──────────────────────────────
    def _ser_vendor_row(self, v):
        return {
            'id': v.id,
            'name': bilingual(v, 'store_name_en') if 'store_name_en' in v._fields
                    else {'en': v.display_name, 'ar': v.display_name},
            'display_name': v.display_name,
            'vendor_type': v.vendor_type or 'seller',
            'tier': v.tier or 'bronze',
            'state': v.state,
            'product_total': v.product_total,
            'score': int(v.uc_score or 0),
            'score_band': v.uc_score_band or 'fair',
            'logo_url': img_url('uellow.vendor', v.id, 'logo_image',
                                unique=v.write_date) if v.logo_image else None,
        }

    @http.route('/api/vendor/v1/admin/vendors', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_vendors(self, **kw):
        p = get_payload()
        search = (p.get('search') or '').strip()
        state = (p.get('state') or '').strip()
        domain = []
        if state:
            domain += [('state', '=', state)]
        if search:
            domain += ['|', ('store_name_en', 'ilike', search),
                            ('store_name_ar', 'ilike', search)]
        Vendor = request.env['uellow.vendor'].sudo()
        rows = Vendor.search(domain, order='total_sales desc', limit=200)
        return ok([self._ser_vendor_row(v) for v in rows])

    CAP_KEYS = ['add_products', 'edit_products', 'archive_products', 'update_stock',
                'publish_products', 'manage_price', 'flash_sale', 'bundles',
                'join_promotions', 'import_products', 'manage_orders',
                'cancel_orders', 'accept_orders', 'restock', 'edit_store',
                'request_payout', 'api', 'live', 'quick_sale']

    @http.route('/api/vendor/v1/admin/vendors/<int:vid>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_vendor_detail(self, vid, **kw):
        v = request.env['uellow.vendor'].sudo().browse(vid)
        if not v.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        s = v._ensure_settings()
        caps = {c: bool(getattr(s, 'cap_' + c, True)) for c in self.CAP_KEYS}
        data = self._ser_vendor_row(v)
        data.update({
            'settings': {
                'vendor_type': s.vendor_type or 'seller',
                'capability_preset': s.capability_preset or 'custom',
                'settlement_mode': s.settlement_mode or 'wallet',
                'hide_financials': bool(s.hide_financials),
                'vendor_sees_customer': bool(s.vendor_sees_customer),
                'caps': caps,
            },
            'stats': {
                'total_sales': v.total_sales, 'order_count': v.order_count,
                'avg_rating': v.avg_rating, 'cancel_rate': v.cancel_rate,
            },
        })
        return ok(data)

    @http.route('/api/vendor/v1/admin/vendors/<int:vid>/settings', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_vendor_settings(self, vid, **kw):
        v = request.env['uellow.vendor'].sudo().browse(vid)
        if not v.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        s = v._ensure_settings()
        p = get_payload()
        vals = {}
        if 'vendor_type' in p:
            vals['vendor_type'] = p['vendor_type']
        if 'settlement_mode' in p:
            vals['settlement_mode'] = p['settlement_mode']
        if 'hide_financials' in p:
            vals['hide_financials'] = bool(p['hide_financials'])
        if 'vendor_sees_customer' in p:
            vals['vendor_sees_customer'] = bool(p['vendor_sees_customer'])
        caps = p.get('caps') or {}
        for c in self.CAP_KEYS:
            if c in caps:
                vals['cap_' + c] = bool(caps[c])
        if vals:
            s.write(vals)
        # optionally re-seed toggles from the (possibly new) vendor_type
        if p.get('apply_preset') and 'vendor_type' in p:
            s._apply_vendor_type_preset()
        out_caps = {c: bool(getattr(s, 'cap_' + c, True)) for c in self.CAP_KEYS}
        return ok({'saved': True, 'caps': out_caps,
                   'vendor_type': s.vendor_type,
                   'settlement_mode': s.settlement_mode,
                   'hide_financials': bool(s.hide_financials)})

    # ───────────────────────── approvals ────────────────────────────
    @http.route('/api/vendor/v1/admin/approvals', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_approvals(self, **kw):
        env = request.env
        changes = env['uellow.product.change'].sudo().search(
            [('state', '=', 'pending')], order='id desc', limit=100)
        new_products = env['product.template'].sudo().search(
            [('vendor_id', '!=', False), ('vendor_approval_state', '=', 'pending')],
            order='vendor_submitted_date desc', limit=100)
        return ok({
            'changes': [{
                'id': c.id,
                'product': c.product_tmpl_id.name,
                'product_id': c.product_tmpl_id.id,
                'vendor': c.vendor_id.display_name or '',
                'summary': c.change_summary or '',
                'when': c.submitted_date.isoformat() if c.submitted_date else '',
            } for c in changes],
            'new_products': [{
                'id': t.id,
                'name': bilingual(t, 'name'),
                'vendor': t.vendor_id.display_name or '',
                'list_price': fmt_price(t.list_price or 0, t.currency_id),
                'image_url': img_url('product.template', t.id, 'image_256',
                                     unique=t.write_date) if t.image_1920 else None,
            } for t in new_products],
            'price_requests': self._price_requests_awaiting(),
        })

    def _price_requests_awaiting(self):
        """Price-update requests with merchant-changed lines awaiting approval."""
        reqs = request.env['uellow.price.request'].sudo().search(
            [('line_ids.line_state', '=', 'await')], order='id desc', limit=50)
        out = []
        for r in reqs:
            awaiting = r.line_ids.filtered(lambda l: l.line_state == 'await')
            if not awaiting:
                continue
            out.append({
                'id': r.id, 'name': r.name,
                'vendor': r.merchant_id.display_name or '',
                'awaiting': len(awaiting),
                'lines': [{
                    'id': l.id,
                    'product': bilingual(l.product_tmpl_id, 'name'),
                    'sku': l.default_code or '',
                    'current_price': round(l.current_price, 3),
                    'new_price': round(l.new_price, 3),
                    'delta_pct': round(l.delta_pct, 1),
                    'margin_after': round(l.new_margin_pct, 1),
                    'image_url': img_url('product.template', l.product_tmpl_id.id,
                                         'image_128', unique=l.product_tmpl_id.write_date)
                                 if l.product_tmpl_id.image_128 else None,
                } for l in awaiting],
            })
        return out

    @http.route('/api/vendor/v1/admin/price-requests/<int:rid>/approve-all',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_price_request_approve_all(self, rid, **kw):
        r = request.env['uellow.price.request'].sudo().browse(rid)
        if not r.exists():
            return fail('NOT_FOUND', 'Request not found', 404)
        r.action_approve_all()
        return ok({'state': r.state})

    @http.route('/api/vendor/v1/admin/price-lines/<int:lid>/<string:decision>',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_price_line_decide(self, lid, decision, **kw):
        ln = request.env['uellow.price.request.line'].sudo().browse(lid)
        if not ln.exists():
            return fail('NOT_FOUND', 'Line not found', 404)
        if decision == 'approve':
            ln.action_approve()
        elif decision == 'reject':
            ln.action_reject()
        else:
            return fail('BAD_DECISION', 'approve or reject', 400)
        # If nothing is left awaiting, mark the request applied.
        req = ln.request_id
        if req and not req.line_ids.filtered(lambda l: l.line_state == 'await'):
            req.state = 'applied'
        return ok({'line_state': ln.line_state})

    @http.route('/api/vendor/v1/admin/changes/<int:cid>/<string:decision>',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_change_decide(self, cid, decision, **kw):
        c = request.env['uellow.product.change'].sudo().browse(cid)
        if not c.exists():
            return fail('NOT_FOUND', 'Change not found', 404)
        if decision == 'approve':
            c.action_approve()
        elif decision == 'reject':
            c.reject_reason = (get_payload().get('reason') or '').strip()
            c.action_reject()
        else:
            return fail('BAD_DECISION', 'approve or reject', 400)
        return ok({'state': c.state})

    @http.route('/api/vendor/v1/admin/products/<int:pid>/<string:decision>',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_product_decide(self, pid, decision, **kw):
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        if decision == 'approve':
            t.action_vendor_approve()
        elif decision == 'reject':
            t.write({'vendor_approval_state': 'rejected',
                     'vendor_rejection_reason': (get_payload().get('reason') or '').strip(),
                     'vendor_reviewed_by': request.env.user.id})
        else:
            return fail('BAD_DECISION', 'approve or reject', 400)
        return ok({'state': t.vendor_approval_state})
