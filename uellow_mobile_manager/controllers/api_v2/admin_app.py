# -*- coding: utf-8 -*-
"""
Admin Console API (v2.2.10)
===========================
Admin-only endpoints powering the in-app admin console (حسابي → 🛡️):

- ``/admin/check``          — is the logged-in app user an admin?
- ``/admin/dashboard``      — sales + POS KPIs, 14-day chart, top products
- ``/admin/orders``         — paginated order list (search + state filter)
- ``/admin/order/<id>``     — full order details
- ``/admin/pos/sessions``   — POS session log (open/close, totals)
- ``/admin/pos/orders``     — recent POS orders
- ``/admin/products``       — product manager list (search)
- ``/admin/product/<id>``   — cost / variants / stock / barcode detail
- ``/admin/product/update`` — write prices, costs, barcodes, continue-selling

Who is an admin? A partner whose linked res.users has Settings-admin or
Sales-manager rights, OR a partner id listed in the ir.config_parameter
``uellow_mobile.admin_partner_ids`` (comma-separated — covers app logins
like Google sign-in that aren't linked to an internal user).
"""
import json
import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (ok, fail, get_payload, safe_endpoint, require_auth,
                      current_partner, img_url)

_logger = logging.getLogger(__name__)

_SALE_STATES = ('sale', 'done')


# ─── admin detection ─────────────────────────────────────────────────
def is_admin_partner(partner):
    """True ONLY for the explicit admin email(s).

    Root fix (2026-06-09): the old check matched ANY user with the broad
    Sales-Manager group and a partner-id allowlist — and because dozens of
    partner records share ali@uellow.com (address/signup duplicates), that
    leaked the console to normal users. The console is now gated strictly on
    the email/login: only ``uellow_mobile.admin_emails`` (default
    ali@uellow.com) qualifies. Data endpoints were always server-checked;
    this also hides the console shell + entry chip.
    """
    if not partner:
        return False
    env = request.env
    raw = (env['ir.config_parameter'].sudo().get_param(
        'uellow_mobile.admin_emails', 'ali@uellow.com') or 'ali@uellow.com')
    allowed = {e.strip().lower() for e in raw.split(',') if e.strip()}
    if not allowed:
        return False
    if (partner.email or '').strip().lower() in allowed:
        return True
    # also accept when the partner's linked login matches (email may differ)
    try:
        for user in partner.sudo().user_ids:
            if (user.login or '').strip().lower() in allowed:
                return True
    except Exception:
        _logger.debug('admin login check failed', exc_info=True)
    return False


def require_admin(fn):
    import functools

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        partner = current_partner()
        if not partner:
            return fail('AUTH_REQUIRED', 'Authentication required', status=401)
        if not is_admin_partner(partner):
            return fail('ADMIN_ONLY', 'Admin access required', status=403)
        return fn(*args, **kwargs)
    return wrapped


# ─── money helpers (admin sees COMPANY currency, no website convert) ──
def _su_env():
    """A real SUPERUSER environment for writes that trigger valuation /
    accounting recomputes which re-check access against the request user
    (public). Mirrors admin_product_update."""
    from odoo import SUPERUSER_ID, api as _api
    return _api.Environment(request.env.cr, SUPERUSER_ID,
                            dict(request.env.context))


def _ccy(env):
    return env.company.currency_id


def _money(env, amount, currency=None):
    cur = currency or _ccy(env)
    digits = cur.decimal_places or 3
    return {'amount': round(float(amount or 0.0), digits),
            'symbol': cur.symbol or 'KD', 'digits': digits,
            'currency': cur.name or 'KWD'}


def _to_company(env, amount, currency):
    """Convert an order amount to company currency for aggregates."""
    try:
        com = _ccy(env)
        if currency and currency.id != com.id:
            from odoo import fields as _f
            return currency._convert(float(amount or 0), com, env.company,
                                     _f.Date.today())
    except Exception:
        pass
    return float(amount or 0)


class UellowAdminAppController(http.Controller):

    # ─── check ────────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/check', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def admin_check(self, **kw):
        return ok({'is_admin': is_admin_partner(current_partner())})

    # ─── dashboard ────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/dashboard', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_dashboard(self, **kw):
        env = request.env
        So = env['sale.order'].sudo()
        now = datetime.now()
        today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # Kuwait is UTC+3 — shift the "day" boundary so today == local today
        today0 = today0 - timedelta(hours=3)

        def _bucket(dfrom, dto=None):
            dom = [('state', 'in', _SALE_STATES),
                   ('date_order', '>=', dfrom.strftime('%Y-%m-%d %H:%M:%S'))]
            if dto:
                dom.append(('date_order', '<', dto.strftime('%Y-%m-%d %H:%M:%S')))
            orders = So.search_read(dom, ['amount_total', 'currency_id'])
            cur_cache = {}
            total = 0.0
            for o in orders:
                cid = o['currency_id'] and o['currency_id'][0]
                if cid not in cur_cache:
                    cur_cache[cid] = env['res.currency'].sudo().browse(cid) \
                        if cid else None
                total += _to_company(env, o['amount_total'], cur_cache[cid])
            n = len(orders)
            return {'count': n, 'total': _money(env, total),
                    'avg': _money(env, (total / n) if n else 0.0)}

        month0 = today0.replace(day=1)
        data = {
            'today':     _bucket(today0),
            'yesterday': _bucket(today0 - timedelta(days=1), today0),
            'week':      _bucket(today0 - timedelta(days=6)),
            'month':     _bucket(month0),
        }

        # ── 14-day revenue series (company ccy) for the chart ──
        days = []
        d14 = today0 - timedelta(days=13)
        rows = So.search_read(
            [('state', 'in', _SALE_STATES),
             ('date_order', '>=', d14.strftime('%Y-%m-%d %H:%M:%S'))],
            ['date_order', 'amount_total', 'currency_id'])
        per_day = {}
        cur_cache = {}
        for r in rows:
            local = r['date_order'] + timedelta(hours=3)
            key = local.strftime('%Y-%m-%d')
            cid = r['currency_id'] and r['currency_id'][0]
            if cid not in cur_cache:
                cur_cache[cid] = env['res.currency'].sudo().browse(cid) \
                    if cid else None
            cell = per_day.setdefault(key, {'total': 0.0, 'count': 0})
            cell['total'] += _to_company(env, r['amount_total'],
                                         cur_cache[cid])
            cell['count'] += 1
        for i in range(14):
            d = (d14 + timedelta(days=i, hours=3)).strftime('%Y-%m-%d')
            cell = per_day.get(d, {'total': 0.0, 'count': 0})
            days.append({'date': d, 'total': round(cell['total'], 3),
                         'count': cell['count']})
        data['daily'] = days

        # ── top products this month ──
        try:
            top = env['sale.order.line'].sudo().read_group(
                [('order_id.state', 'in', _SALE_STATES),
                 ('order_id.date_order', '>=',
                  month0.strftime('%Y-%m-%d %H:%M:%S')),
                 ('product_id', '!=', False),
                 ('is_delivery', '=', False)],
                ['product_uom_qty:sum', 'price_total:sum'],
                ['product_id'], limit=6, orderby='price_total desc')
            tops = []
            for g in top:
                pid = g['product_id'] and g['product_id'][0]
                if not pid:
                    continue
                prod = env['product.product'].sudo().browse(pid)
                tops.append({
                    'id': prod.product_tmpl_id.id,
                    'name': g['product_id'][1],
                    'image': img_url('product.product', pid, 'image_128',
                                     unique=prod.write_date),
                    'qty': int(g.get('product_uom_qty') or 0),
                    'total': _money(env, g.get('price_total') or 0.0),
                })
            data['top_products'] = tops
        except Exception:
            _logger.debug('top products failed', exc_info=True)
            data['top_products'] = []

        # ── sales by website this month (converted to company ccy) ──
        try:
            wrows = So.search_read(
                [('state', 'in', _SALE_STATES),
                 ('date_order', '>=', month0.strftime('%Y-%m-%d %H:%M:%S'))],
                ['website_id', 'amount_total', 'currency_id'])
            agg = {}
            for r in wrows:
                wname = (r['website_id'] and r['website_id'][1]) \
                    or 'Backend / POS'
                cid = r['currency_id'] and r['currency_id'][0]
                if cid not in cur_cache:
                    cur_cache[cid] = env['res.currency'].sudo().browse(cid) \
                        if cid else None
                cell = agg.setdefault(wname, {'count': 0, 'total': 0.0})
                cell['count'] += 1
                cell['total'] += _to_company(env, r['amount_total'],
                                             cur_cache[cid])
            sites = [{'website': k, 'count': v['count'],
                      'total': round(v['total'], 3)}
                     for k, v in agg.items()]
            sites.sort(key=lambda s: -s['total'])
            data['by_website'] = sites[:8]
        except Exception:
            data['by_website'] = []

        # ── POS snapshot ──
        pos = {'available': 'pos.order' in env}
        if pos['available']:
            try:
                Po = env['pos.order'].sudo()
                pdom = [('date_order', '>=',
                         today0.strftime('%Y-%m-%d %H:%M:%S'))]
                porders = Po.search_read(pdom, ['amount_total'])
                pos['today_count'] = len(porders)
                pos['today_total'] = _money(
                    env, sum(p['amount_total'] for p in porders))
                opens = env['pos.session'].sudo().search(
                    [('state', 'not in', ('closed',))], limit=10)
                pos['open_sessions'] = [{
                    'id': s.id, 'name': s.name,
                    'config': s.config_id.name or '',
                    'user': s.user_id.name or '',
                    'state': s.state,
                    'start_at': s.start_at and
                    (s.start_at + timedelta(hours=3))
                    .strftime('%Y-%m-%d %H:%M') or '',
                    'orders': env['pos.order'].sudo().search_count(
                        [('session_id', '=', s.id)]),
                } for s in opens]
            except Exception:
                _logger.debug('pos snapshot failed', exc_info=True)
                pos = {'available': False}
        data['pos'] = pos

        # ── pending counts ──
        try:
            data['pending'] = {
                'quotations': So.search_count([('state', '=', 'draft'),
                                               ('website_id', '!=', False)]),
                'to_deliver': So.search_count(
                    [('state', 'in', _SALE_STATES),
                     ('date_order', '>=', (today0 - timedelta(days=30))
                      .strftime('%Y-%m-%d %H:%M:%S')),
                     ('delivery_status', 'not in',
                      ('delivered', 'cancelled', 'failed'))]),
            }
        except Exception:
            data['pending'] = {'quotations': 0, 'to_deliver': 0}
        return ok(data)

    # ─── orders list ──────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_orders(self, **kw):
        env = request.env
        So = env['sale.order'].sudo()
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        dom = []
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q),
                    ('partner_id.name', 'ilike', q),
                    ('partner_id.phone', 'ilike', q)]
        state = (kw.get('state') or '').strip()
        if state == 'quotation':
            dom.append(('state', 'in', ('draft', 'sent')))
        elif state == 'sale':
            dom.append(('state', 'in', _SALE_STATES))
        elif state == 'cancel':
            dom.append(('state', '=', 'cancel'))
        else:
            # default view: real orders only (not abandoned carts)
            dom.append(('state', 'in', _SALE_STATES + ('cancel',)))
        total = So.search_count(dom)
        orders = So.search(dom, order='date_order desc',
                           limit=per, offset=(page - 1) * per)
        rows = []
        for o in orders:
            rows.append({
                'id': o.id, 'name': o.name,
                'date': o.date_order and
                (o.date_order + timedelta(hours=3))
                .strftime('%Y-%m-%d %H:%M') or '',
                'customer': o.partner_id.name or '',
                'phone': o.partner_id.phone or o.partner_id.mobile or '',
                'state': o.state,
                'delivery_status': getattr(o, 'delivery_status', '') or '',
                'website': o.website_id.name or 'Backend',
                'items': int(sum(l.product_uom_qty for l in o.order_line
                                 if not l.is_delivery)),
                'total': _money(env, o.amount_total, o.currency_id),
                'payment': (o.transaction_ids[:1].provider_id.name
                            if o.transaction_ids else
                            ('COD' if getattr(o, 'carrier_id', False)
                             else '')) or '',
            })
        return ok({'orders': rows, 'page': page, 'per_page': per,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── order detail ─────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_detail(self, order_id, **kw):
        env = request.env
        o = env['sale.order'].sudo().browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        lines = []
        for l in o.order_line:
            if l.is_delivery:
                continue
            p = l.product_id
            lines.append({
                'name': l.name or p.display_name,
                'image': p and img_url('product.product', p.id, 'image_128',
                                       unique=p.write_date) or '',
                'qty': l.product_uom_qty,
                'price_unit': round(l.price_unit, 3),
                'total': round(l.price_total, 3),
            })
        ship = o.partner_shipping_id
        txs = [{
            'provider': t.provider_id.name or '', 'state': t.state,
            'amount': round(t.amount, 3), 'ref': t.reference or '',
        } for t in o.transaction_ids]
        data = {
            'id': o.id, 'name': o.name, 'state': o.state,
            'date': o.date_order and
            (o.date_order + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M') or '',
            'website': o.website_id.name or 'Backend',
            'delivery_status': getattr(o, 'delivery_status', '') or '',
            'customer': {
                'id': o.partner_id.id,
                'name': o.partner_id.name or '',
                'phone': o.partner_id.phone or o.partner_id.mobile or '',
                'email': o.partner_id.email or '',
            },
            'shipping_address': ', '.join(filter(None, [
                ship.street, ship.street2, ship.city,
                ship.state_id.name if ship.state_id else '',
                ship.country_id.name if ship.country_id else ''])),
            'carrier': o.carrier_id.name or '',
            'lines': lines,
            'transactions': txs,
            'amounts': {
                'untaxed': _money(env, o.amount_untaxed, o.currency_id),
                'delivery': _money(env, sum(
                    l.price_total for l in o.order_line if l.is_delivery),
                    o.currency_id),
                'tax': _money(env, o.amount_tax, o.currency_id),
                'total': _money(env, o.amount_total, o.currency_id),
            },
            'note': o.note and str(o.note)[:500] or '',
        }
        return ok(data)

    # ─── POS sessions ─────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/pos/sessions', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_sessions(self, **kw):
        env = request.env
        if 'pos.session' not in env:
            return ok({'sessions': [], 'available': False})
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        Sess = env['pos.session'].sudo()
        total = Sess.search_count([])
        sessions = Sess.search([], order='id desc', limit=per,
                               offset=(page - 1) * per)
        Po = env['pos.order'].sudo()
        rows = []
        for s in sessions:
            orders = Po.search_read([('session_id', '=', s.id)],
                                    ['amount_total'])
            rows.append({
                'id': s.id, 'name': s.name,
                'config': s.config_id.name or '',
                'user': s.user_id.name or '',
                'state': s.state,
                'start_at': s.start_at and
                (s.start_at + timedelta(hours=3))
                .strftime('%Y-%m-%d %H:%M') or '',
                'stop_at': s.stop_at and
                (s.stop_at + timedelta(hours=3))
                .strftime('%Y-%m-%d %H:%M') or '',
                'orders': len(orders),
                'total': _money(env, sum(o['amount_total'] for o in orders)),
                'cash_open': round(s.cash_register_balance_start or 0, 3)
                if 'cash_register_balance_start' in s._fields else 0,
                'cash_close': round(s.cash_register_balance_end_real or 0, 3)
                if 'cash_register_balance_end_real' in s._fields else 0,
            })
        return ok({'sessions': rows, 'available': True, 'page': page,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── POS orders ───────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/pos/orders', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_orders(self, **kw):
        env = request.env
        if 'pos.order' not in env:
            return ok({'orders': [], 'available': False})
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        dom = []
        if kw.get('session_id'):
            dom.append(('session_id', '=', int(kw['session_id'])))
        Po = env['pos.order'].sudo()
        total = Po.search_count(dom)
        orders = Po.search(dom, order='id desc', limit=per,
                           offset=(page - 1) * per)
        rows = []
        for o in orders:
            rows.append({
                'id': o.id, 'name': o.name or o.pos_reference or '',
                'date': o.date_order and
                (o.date_order + timedelta(hours=3))
                .strftime('%Y-%m-%d %H:%M') or '',
                'session': o.session_id.name or '',
                'cashier': (o.employee_id.name
                            if 'employee_id' in o._fields and o.employee_id
                            else o.user_id.name) or '',
                'customer': o.partner_id.name or '',
                'state': o.state,
                'items': int(sum(l.qty for l in o.lines)),
                'lines': [{'name': l.product_id.display_name or '',
                           'qty': l.qty,
                           'total': round(l.price_subtotal_incl, 3)}
                          for l in o.lines[:20]],
                'total': _money(env, o.amount_total, o.currency_id),
                'payments': [{'method': p.payment_method_id.name or '',
                              'amount': round(p.amount, 3)}
                             for p in o.payment_ids],
            })
        return ok({'orders': rows, 'available': True, 'page': page,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── products list ────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/products', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_products(self, **kw):
        env = request.env
        Tmpl = env['product.template'].sudo()
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        dom = [('sale_ok', '=', True)]
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q),
                    ('default_code', 'ilike', q),
                    ('product_variant_ids.barcode', 'ilike', q)]
        total = Tmpl.search_count(dom)
        tmpls = Tmpl.search(dom, order='write_date desc', limit=per,
                            offset=(page - 1) * per)
        rows = []
        for t in tmpls:
            rows.append({
                'id': t.id,
                'name': t.with_context(lang='en_US').name or t.name,
                'name_ar': t.with_context(lang='ar_001').name or '',
                'image': img_url('product.template', t.id, 'image_256',
                                 unique=t.write_date),
                'price': round(t.list_price, 3),
                'cost': round(t.product_variant_ids[:1].standard_price
                              or t.standard_price, 3),
                'qty': round(t.qty_available, 1),
                'variants': len(t.product_variant_ids),
                'barcode': t.product_variant_ids[:1].barcode or '',
                'continue_selling': bool(
                    getattr(t, 'allow_out_of_stock_order', False)),
                'published': bool(t.is_published),
            })
        return ok({'products': rows, 'page': page, 'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── product admin detail ─────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/product/<int:tmpl_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_product_detail(self, tmpl_id, **kw):
        env = request.env
        t = env['product.template'].sudo().browse(tmpl_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Product not found', status=404)
        variants = []
        for v in t.product_variant_ids:
            attrs = ', '.join(
                v.product_template_attribute_value_ids.mapped('name')) or ''
            variants.append({
                'id': v.id,
                'attrs': attrs,
                'image': img_url('product.product', v.id, 'image_128',
                                 unique=v.write_date),
                'cost': round(v.standard_price, 3),
                'price': round(v.lst_price, 3),
                'qty': round(v.qty_available, 1),
                'barcode': v.barcode or '',
                'sku': v.default_code or '',
            })
        cur = _ccy(env)
        data = {
            'id': t.id,
            'name': t.with_context(lang='en_US').name or t.name,
            'name_ar': t.with_context(lang='ar_001').name or '',
            'image': img_url('product.template', t.id, 'image_512',
                             unique=t.write_date),
            'price': round(t.list_price, 3),
            'cost': round(t.product_variant_ids[:1].standard_price
                          or t.standard_price, 3),
            'qty': round(t.qty_available, 1),
            'is_storable': bool(getattr(t, 'is_storable', True)),
            'continue_selling': bool(
                getattr(t, 'allow_out_of_stock_order', False)),
            'barcode': t.product_variant_ids[:1].barcode or '',
            'has_variants': len(t.product_variant_ids) > 1,
            'variants': variants,
            'currency': {'symbol': cur.symbol or 'KD',
                         'digits': cur.decimal_places or 3},
            'published': bool(t.is_published),
            # v2.2.41 — current eCommerce categories (for the admin section picker)
            'eco_categories': [{'id': c.id, 'name': c.display_name}
                               for c in t.public_categ_ids],
        }
        return ok(data)

    # ─── product update ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/product/update', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_product_update(self, **kw):
        # Writes run as the SUPERUSER (not just sudo): standard_price
        # triggers stock-valuation recomputes that re-check access with
        # the request user (public) and would raise AccessError.
        from odoo import SUPERUSER_ID, api as _api
        env = _api.Environment(request.env.cr, SUPERUSER_ID,
                               dict(request.env.context))
        p = get_payload()
        tmpl_id = int(p.get('id') or 0)
        t = env['product.template'].sudo().browse(tmpl_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Product not found', status=404)
        changed = []
        try:
            tvals = {}
            if p.get('price') is not None:
                tvals['list_price'] = float(p['price'])
                changed.append('price')
            if p.get('continue_selling') is not None:
                tvals['allow_out_of_stock_order'] = bool(p['continue_selling'])
                changed.append('continue_selling')
            # v2.2.41 — eCommerce category (section) edit from the admin sheet.
            if p.get('public_categ_ids') is not None:
                ids = [int(c) for c in p['public_categ_ids'] if str(c).strip()]
                tvals['public_categ_ids'] = [(6, 0, ids)]
                changed.append('categories')
            if tvals:
                t.write(tvals)
            # cost lives on the VARIANT (company-dependent property)
            if p.get('cost') is not None and len(t.product_variant_ids) == 1:
                t.product_variant_ids.standard_price = float(p['cost'])
                changed.append('cost')
            if p.get('barcode') is not None \
                    and len(t.product_variant_ids) == 1:
                bc = (p['barcode'] or '').strip()
                t.product_variant_ids.barcode = bc or False
                changed.append('barcode')
            for vv in (p.get('variants') or []):
                v = env['product.product'].sudo().browse(
                    int(vv.get('id') or 0)).exists()
                if not v or v.product_tmpl_id.id != t.id:
                    continue
                if vv.get('cost') is not None:
                    v.standard_price = float(vv['cost'])
                    changed.append('variant_cost')
                if vv.get('barcode') is not None:
                    bc = (vv['barcode'] or '').strip()
                    v.barcode = bc or False
                    changed.append('variant_barcode')
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            msg = str(e)
            if 'barcode' in msg.lower() and ('unique' in msg.lower()
                                             or 'duplicate' in msg.lower()):
                return fail('BARCODE_DUP',
                            'This barcode is already used by another product',
                            status=400)
            _logger.warning('admin product update failed', exc_info=True)
            return fail('UPDATE_FAILED', msg[:200], status=400)
        return ok({'updated': sorted(set(changed))})

    # ─── eCommerce category picker (product section editor) ─────────────
    @http.route('/api/mobile/v2/admin/categories', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_categories(self, **kw):
        Cat = request.env['product.public.category'].sudo()
        order = 'complete_name' if 'complete_name' in Cat._fields else 'name'
        cats = Cat.search([], order=order)
        return ok({'categories': [
            {'id': c.id,
             'name': (getattr(c, 'complete_name', False) or c.display_name
                      or c.name or '')} for c in cats]})

    # ─── order: approve / confirm ──────────────────────────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/approve',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_approve(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        if o.state in ('sale', 'done'):
            return ok({'state': o.state, 'already': True})
        try:
            o.action_confirm()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CONFIRM_FAILED', str(e)[:200], status=400)
        return ok({'state': o.state})

    # ─── order: cancel ─────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/cancel',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_cancel(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        try:
            o.with_context(disable_cancel_warning=True).action_cancel()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CANCEL_FAILED', str(e)[:200], status=400)
        return ok({'state': o.state})

    # ─── delivery: assignment options (carriers / drivers / rules) ─────
    @http.route('/api/mobile/v2/admin/delivery/options', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_delivery_options(self, **kw):
        env = request.env
        out = {'carrier_companies': [], 'drivers': [], 'pricing_rules': []}
        if 'delivery.carrier.company' in env:
            CC = env['delivery.carrier.company'].sudo()
            dom = [('active', '=', True)] if 'active' in CC._fields else []
            for c in CC.search(dom):
                out['carrier_companies'].append({'id': c.id, 'name': c.name})
        if 'delivery.driver' in env:
            for d in env['delivery.driver'].sudo().search([]):
                out['drivers'].append({
                    'id': d.id, 'name': d.name,
                    'carrier_company_id': d.carrier_company_id.id
                    if getattr(d, 'carrier_company_id', False) else None})
        if 'carrier.pricing.rule' in env:
            for r in env['carrier.pricing.rule'].sudo().search([]):
                out['pricing_rules'].append({
                    'id': r.id, 'name': r.display_name,
                    'carrier_company_id': r.carrier_company_id.id
                    if getattr(r, 'carrier_company_id', False) else None})
        return ok(out)

    # ─── delivery: assign a single order (reuses the back-office wizard) ─
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/assign-delivery',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_assign_delivery(self, order_id, **kw):
        env = _su_env()
        if 'delivery.assign.wizard' not in env:
            return fail('UNSUPPORTED', 'Delivery module not installed', 400)
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        p = get_payload()
        cc = int(p.get('carrier_company_id') or 0)
        if not cc:
            return fail('BAD_REQUEST', 'carrier_company_id is required', 400)
        wiz_vals = {'order_ids': [(6, 0, [o.id])], 'carrier_company_id': cc}
        for fld in ('driver_id', 'pricing_rule_id'):
            if p.get(fld):
                wiz_vals[fld] = int(p[fld])
        if p.get('payment_method_type'):
            wiz_vals['payment_method_type'] = p['payment_method_type']
        if p.get('set_status'):
            wiz_vals['set_status'] = p['set_status']
        if p.get('create_trip') is not None:
            wiz_vals['create_trip'] = bool(p['create_trip'])
        try:
            wiz = env['delivery.assign.wizard'].create(wiz_vals)
            wiz.action_assign()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('ASSIGN_FAILED', str(e)[:200], status=400)
        return ok({'delivery_status': getattr(o, 'delivery_status', ''),
                   'carrier': o.carrier_id.name if o.carrier_id else ''})

    # ─── order: create a new draft order ───────────────────────────────
    @http.route('/api/mobile/v2/admin/order/create', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_create(self, **kw):
        env = _su_env()
        p = get_payload()
        partner = None
        partner_id = int(p.get('partner_id') or 0)
        if partner_id:
            partner = env['res.partner'].browse(partner_id).exists()
        if not partner:
            name = (p.get('customer_name') or '').strip()
            phone = (p.get('customer_phone') or '').strip()
            if not name and not phone:
                return fail('BAD_REQUEST',
                            'partner_id or customer name/phone required', 400)
            if phone:
                partner = env['res.partner'].search(
                    [('phone', '=', phone)], limit=1)
            if not partner:
                partner = env['res.partner'].create(
                    {'name': name or phone, 'phone': phone or False})
        order_lines = []
        for ln in (p.get('lines') or []):
            pid = int(ln.get('product_id') or 0)
            qty = float(ln.get('qty') or 1)
            if pid <= 0:
                continue
            prod = env['product.product'].browse(pid).exists()
            if not prod:
                tmpl = env['product.template'].browse(pid).exists()
                prod = tmpl.product_variant_ids[:1] if tmpl else None
            if not prod:
                continue
            order_lines.append((0, 0, {'product_id': prod.id,
                                       'product_uom_qty': qty}))
        if not order_lines:
            return fail('BAD_REQUEST', 'At least one valid line is required',
                        400)
        try:
            order = env['sale.order'].create({
                'partner_id': partner.id, 'order_line': order_lines})
            if bool(p.get('confirm')):
                order.action_confirm()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CREATE_FAILED', str(e)[:200], status=400)
        return ok({'order_id': order.id, 'order_name': order.name,
                   'state': order.state,
                   'amount_total': round(order.amount_total, 3)})
