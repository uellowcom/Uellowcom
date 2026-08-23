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
- ``/admin/helpdesk/meta``   — support KPIs + teams + stages (filter chips)
- ``/admin/helpdesk/tickets``— paginated ticket list (search + filters)
- ``/admin/helpdesk/ticket/<id>``        — full ticket detail + chatter thread
- ``/admin/helpdesk/ticket/<id>/reply``  — public reply or internal note
- ``/admin/helpdesk/ticket/<id>/stage``  — move stage / close
- ``/admin/helpdesk/ticket/<id>/assign`` — (re)assign to a user
- ``/admin/helpdesk/agents`` — assignable helpdesk agents

Who is an admin? A partner whose linked res.users has Settings-admin or
Sales-manager rights, OR a partner id listed in the ir.config_parameter
``uellow_mobile.admin_partner_ids`` (comma-separated — covers app logins
like Google sign-in that aren't linked to an internal user).
"""
import base64
import json
import logging
import urllib.parse
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


def _pos_line_cost(line):
    """Best-effort cost of a POS order line for profit/margin.

    Prefer POS's own stored `total_cost` (signed for refunds); fall back to
    the variant's standard_price × qty when the field is absent or zero.
    """
    try:
        tc = getattr(line, 'total_cost', None)
        if tc:
            return float(tc)
    except Exception:
        pass
    try:
        unit = float(getattr(line.product_id, 'standard_price', 0.0) or 0.0)
        return unit * float(line.qty or 0.0)
    except Exception:
        return 0.0


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

        # ── live / realtime snapshot (v2.2.46) ──
        # Who is on the app right now + reach metrics the admin actually
        # wants on the home screen.
        live = {}
        try:
            MS = env['mobile.session'].sudo()
            now = datetime.now()
            t0s = today0.strftime('%Y-%m-%d %H:%M:%S')
            live['online_now'] = MS.search_count([
                ('last_activity', '>=', now - timedelta(minutes=5)),
                ('is_revoked', '=', False)])
            live['active_30m'] = MS.search_count([
                ('last_activity', '>=', now - timedelta(minutes=30)),
                ('is_revoked', '=', False)])
            live['active_today'] = MS.search_count([
                ('last_activity', '>=', t0s), ('is_revoked', '=', False)])
            P = env['res.partner'].sudo()
            live['push_reach'] = P.search_count([('fcm_token', '!=', False)])
            live['new_customers_today'] = P.search_count([
                ('create_date', '>=', t0s), ('customer_rank', '>', 0)])
            live['carts_active'] = So.search_count([
                ('state', '=', 'draft'), ('website_id', '!=', False),
                ('write_date', '>=', now - timedelta(hours=2))])
        except Exception:
            _logger.debug('live snapshot failed', exc_info=True)
        data['live'] = live
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
        order_cost = 0.0
        for l in o.order_line:
            if l.is_delivery:
                continue
            p = l.product_id
            # Per-line profit: prefer the sale_margin field, else derive from
            # the variant cost (standard_price). Free/gift lines (price 0 but
            # real cost) correctly show a negative margin.
            try:
                lcost = float(getattr(p, 'standard_price', 0.0) or 0.0) \
                    * (l.product_uom_qty or 0.0)
            except Exception:
                lcost = 0.0
            order_cost += lcost
            lmargin = getattr(l, 'margin', None)
            if lmargin is None:
                lmargin = round(l.price_subtotal - lcost, 3)
            lines.append({
                'name': l.name or p.display_name,
                'image': p and img_url('product.product', p.id, 'image_128',
                                       unique=p.write_date) or '',
                'qty': l.product_uom_qty,
                'price_unit': round(l.price_unit, 3),
                'total': round(l.price_total, 3),
                'cost': round(lcost, 3),
                'margin': round(lmargin, 3),
            })
        ship = o.partner_shipping_id
        txs = [{
            'provider': t.provider_id.name or '', 'state': t.state,
            'amount': round(t.amount, 3), 'ref': t.reference or '',
        } for t in o.transaction_ids]
        # Profit for the whole order — prefer sale_margin's stored value.
        try:
            margin = getattr(o, 'margin', None)
            if margin is None:
                margin = o.amount_untaxed - order_cost
            margin = round(margin, 3)
        except Exception:
            margin = round(o.amount_untaxed - order_cost, 3)
        # Invoices + pickings + lock state for the full action set.
        invoices = [{
            'id': inv.id, 'name': inv.name or '/',
            'state': inv.state, 'payment_state': inv.payment_state or '',
            'amount': round(inv.amount_total, 3),
        } for inv in o.invoice_ids]
        pickings = [{
            'id': pk.id, 'name': pk.name or '',
            'state': pk.state,
        } for pk in getattr(o, 'picking_ids', [])]
        locked = bool(getattr(o, 'locked', False))
        # Custom delivery stack (delivery_carrier_portal) — the real carrier
        # company / driver / status the assign wizard writes, NOT carrier_id.
        deliv = {
            'company': getattr(o, 'delivery_carrier_company_id', False)
            and o.delivery_carrier_company_id.name or '',
            'driver': getattr(o, 'delivery_driver_id', False)
            and o.delivery_driver_id.name or '',
            'status': getattr(o, 'delivery_status', '') or '',
            'carrier': o.carrier_id.name or '',
            'paid_online': bool(getattr(o, 'upayments_paid', False)),
        }
        confirmed = o.state in ('sale', 'done')
        data = {
            'id': o.id, 'name': o.name, 'state': o.state,
            'locked': locked,
            'invoice_status': getattr(o, 'invoice_status', '') or '',
            'date': o.date_order and
            (o.date_order + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M') or '',
            'website': o.website_id.name or 'Backend',
            'delivery_status': getattr(o, 'delivery_status', '') or '',
            'delivery': deliv,
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
            'carrier': deliv['company'] or o.carrier_id.name or '',
            'lines': lines,
            'transactions': txs,
            'invoices': invoices,
            'pickings': pickings,
            'amounts': {
                'untaxed': _money(env, o.amount_untaxed, o.currency_id),
                'delivery': _money(env, sum(
                    l.price_total for l in o.order_line if l.is_delivery),
                    o.currency_id),
                'tax': _money(env, o.amount_tax, o.currency_id),
                'total': _money(env, o.amount_total, o.currency_id),
                'cost': _money(env, order_cost, o.currency_id),
                'margin': _money(env, margin, o.currency_id),
            },
            # Action flags so the app shows only the relevant buttons.
            'can': {
                'confirm': o.state in ('draft', 'sent'),
                'cancel': o.state != 'cancel',
                'assign_delivery': confirmed,
                'invoice': confirmed and o.invoice_status == 'to invoice',
                'deliver': bool([pk for pk in getattr(o, 'picking_ids', [])
                                 if pk.state not in ('done', 'cancel')]),
                'register_payment': bool([
                    inv for inv in o.invoice_ids
                    if inv.state == 'posted'
                    and inv.payment_state in ('not_paid', 'partial')]),
                'lock': confirmed and not locked,
                'unlock': locked,
                # Online charge known to the gateway but not captured here —
                # offer a manual reconcile (heals a missed webhook).
                'verify_payment': bool(
                    getattr(o, 'upayments_track_id', False))
                and not bool(getattr(o, 'upayments_paid', False)),
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
        dom = []
        if kw.get('state'):
            dom.append(('state', '=', kw.get('state')))
        for _f, _k in (('config_id', 'config_id'), ('user_id', 'user_id')):
            if kw.get('_k' if False else _k):
                try:
                    dom.append((_f, '=', int(kw.get(_k))))
                except Exception:
                    pass
        if kw.get('date_from'):
            dom.append(('start_at', '>=', kw.get('date_from')))
        if kw.get('date_to'):
            dom.append(('start_at', '<=', kw.get('date_to') + ' 23:59:59'))
        total = Sess.search_count(dom)
        sessions = Sess.search(dom, order='id desc', limit=per,
                               offset=(page - 1) * per)
        Po = env['pos.order'].sudo()
        rows = []
        for s in sessions:
            orders = Po.search([('session_id', '=', s.id)])
            sales = sum(o.amount_total for o in orders)
            # Profit = Σ line margin (prefer pos.order.line.margin, else
            # derive from the product cost) across all session orders.
            cost = 0.0
            items = 0
            refunds = 0.0
            for o in orders:
                if o.amount_total < 0:
                    refunds += o.amount_total
                for l in o.lines:
                    items += abs(int(l.qty or 0))
                    cost += _pos_line_cost(l)
            profit = round(sales - cost, 3)
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
                'items': items,
                'total': _money(env, sales),
                'cost': _money(env, cost),
                'profit': _money(env, profit),
                'margin_pct': round((profit / sales * 100), 1) if sales else 0,
                'refunds': _money(env, refunds),
                'cash_open': round(s.cash_register_balance_start or 0, 3)
                if 'cash_register_balance_start' in s._fields else 0,
                'cash_close': round(s.cash_register_balance_end_real or 0, 3)
                if 'cash_register_balance_end_real' in s._fields else 0,
            })
        return ok({'sessions': rows, 'available': True, 'page': page,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── POS session DETAIL: payments (cash/knet) + products sold ──────
    @http.route('/api/mobile/v2/admin/pos/session/<int:session_id>',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_session_detail(self, session_id, **kw):
        env = request.env
        if 'pos.session' not in env:
            return ok({'available': False})
        s = env['pos.session'].sudo().browse(session_id)
        if not s.exists():
            return fail('NOT_FOUND', 'Session not found', 404)
        Po = env['pos.order'].sudo()
        orders = Po.search([('session_id', '=', s.id)])
        from collections import defaultdict
        # ── payments by method (Cash / Card=KNET / installments / ...) ──
        pm = defaultdict(lambda: {'amount': 0.0, 'count': 0})
        try:
            for p in env['pos.payment'].sudo().search([('session_id', '=', s.id)]):
                k = (p.payment_method_id.name or 'Other')
                pm[k]['amount'] += p.amount
                pm[k]['count'] += 1
        except Exception:
            pass
        payments = [{'method': k,
                     'amount': _money(env, v['amount']),
                     'amount_raw': round(v['amount'], 3),
                     'count': v['count']}
                    for k, v in sorted(pm.items(), key=lambda x: -x[1]['amount'])]

        def _sum_like(subs):
            return round(sum(v['amount'] for k, v in pm.items()
                             if any(n in (k or '').lower() for n in subs)), 3)
        cash_total = _sum_like(['cash', 'نقد', 'كاش'])
        knet_total = _sum_like(['card', 'knet', 'k-net', 'كي', 'بطاق', 'شبك'])
        # ── products sold (aggregate by variant) ──
        prod = {}
        sales = 0.0
        refunds = 0.0
        items = 0
        cost = 0.0
        for o in orders:
            sales += o.amount_total
            if o.amount_total < 0:
                refunds += o.amount_total
            for l in o.lines:
                pv = l.product_id
                e = prod.setdefault(pv.id, {
                    'id': pv.product_tmpl_id.id, 'name': (pv.name or ''),
                    'qty': 0.0, 'total': 0.0, 'cost': 0.0,
                    'barcode': pv.barcode or ''})
                q = l.qty or 0
                e['qty'] += q
                e['total'] += (l.price_subtotal_incl or 0)
                lc = _pos_line_cost(l)
                e['cost'] += lc
                items += abs(int(q))
                cost += lc
        products = sorted(prod.values(), key=lambda x: -x['total'])
        products = [{'id': p['id'], 'name': p['name'], 'barcode': p['barcode'],
                     'qty': round(p['qty'], 2),
                     'total': _money(env, p['total']),
                     'total_raw': round(p['total'], 3),
                     'profit': _money(env, p['total'] - p['cost'])}
                    for p in products]
        profit = round(sales - cost, 3)
        session = {
            'id': s.id, 'name': s.name,
            'config': s.config_id.name or '',
            'user': s.user_id.name or '',
            'state': s.state,
            'start_at': s.start_at and (s.start_at + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M') or '',
            'stop_at': s.stop_at and (s.stop_at + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M') or '',
            'orders': len(orders),
            'items': items,
            'total': _money(env, sales),
            'cost': _money(env, cost),
            'profit': _money(env, profit),
            'margin_pct': round((profit / sales * 100), 1) if sales else 0,
            'refunds': _money(env, refunds),
            'cash_open': round(s.cash_register_balance_start or 0, 3)
            if 'cash_register_balance_start' in s._fields else 0,
            'cash_close': round(s.cash_register_balance_end_real or 0, 3)
            if 'cash_register_balance_end_real' in s._fields else 0,
        }
        return ok({'available': True, 'session': session,
                   'payments': payments,
                   'cash_total': _money(env, cash_total),
                   'cash_total_raw': cash_total,
                   'knet_total': _money(env, knet_total),
                   'knet_total_raw': knet_total,
                   'products': products,
                   'products_count': len(products)})

    # ─── Purchase order PDF print ─────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/print',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_print(self, po_id, **kw):
        env = request.env
        po = env['purchase.order'].sudo().browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', 404)
        ref = ('uellow_documents.uellow_purchaseorder'
               if env.ref('uellow_documents.uellow_purchaseorder', raise_if_not_found=False)
               else 'purchase.report_purchasequotation')
        pdf, _ct = env['ir.actions.report'].sudo()._render_qweb_pdf(ref, [po.id])
        fn = (po.name or ('PO-%s' % po.id)).replace('/', '-')
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="%s.pdf"' % fn)])

    # ─── POS order 80mm thermal receipt (HTML, same as the POS receipt) ─
    @http.route('/api/mobile/v2/admin/pos/order/<int:order_id>/receipt',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_order_receipt(self, order_id, **kw):
        env = request.env
        o = env['pos.order'].sudo().browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'POS order not found', 404)
        from odoo.tools import html_escape as _e
        cur = o.currency_id or env.company.currency_id
        sym = cur.symbol or cur.name

        def _m(a):
            return '%s %s' % (('%.3f' % (a or 0)), sym)
        shop = _e(o.config_id.name or (o.company_id.name if o.company_id else 'Uellow'))
        when = (o.date_order + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M') if o.date_order else ''
        rows = ''
        for l in o.lines:
            rows += (
                '<tr><td class="n">%s</td><td class="q">%sx</td>'
                '<td class="p">%s</td></tr>'
                '<tr><td colspan="2" class="u">%s</td><td class="p">%s</td></tr>' % (
                    _e(l.product_id.name or ''), ('%g' % (l.qty or 0)),
                    _e(_m(l.price_subtotal_incl or 0)),
                    _e('@ ' + _m(l.price_unit or 0)),
                    ''))
        pays = ''
        for p in o.payment_ids:
            pays += '<tr><td class="n">%s</td><td class="p">%s</td></tr>' % (
                _e(p.payment_method_id.name or ''), _e(_m(p.amount or 0)))
        html = (
            '<!doctype html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex"><title>Receipt %s</title>'
            '<style>@page{size:80mm auto;margin:0}'
            'body{width:80mm;margin:0 auto;padding:8px 10px;font-family:'
            '\'Tajawal\',monospace,sans-serif;font-size:12px;color:#000}'
            '.c{text-align:center}.b{font-weight:800}.big{font-size:16px}'
            'hr{border:0;border-top:1px dashed #000;margin:6px 0}'
            'table{width:100%%;border-collapse:collapse}'
            'td.q{text-align:center;width:34px}td.p{text-align:right;white-space:nowrap}'
            'td.u{color:#555;font-size:10px;padding-bottom:3px}'
            'td.n{word-break:break-word}.tot{font-size:14px;font-weight:800}'
            '.pay{font-weight:700}@media print{button{display:none}}'
            'button{width:100%%;padding:10px;margin-top:10px;font-size:14px;'
            'font-weight:800;border:0;background:#111;color:#fff;border-radius:8px}'
            '</style></head><body>'
            '<div class="c b big">%s</div>'
            '<div class="c">%s</div><div class="c">%s</div>'
            '<hr><table>%s</table><hr>'
            '<table>'
            '<tr><td class="n">\u0627\u0644\u0625\u062c\u0645\u0627\u0644\u064a</td><td class="p tot">%s</td></tr>'
            '<tr><td class="n">\u0627\u0644\u0636\u0631\u064a\u0628\u0629</td><td class="p">%s</td></tr>'
            '</table><hr><div class="pay">\u0627\u0644\u062f\u0641\u0639:</div>'
            '<table>%s</table><hr>'
            '<div class="c">\u0634\u0643\u0631\u0627\u064b \u0644\u0632\u064a\u0627\u0631\u062a\u0643\u0645 \ud83d\udc1d</div>'
            '<button onclick="window.print()">\u0637\u0628\u0627\u0639\u0629 \ud83d\udda8\ufe0f</button>'
            '</body></html>') % (
                _e(o.name or str(o.id)), shop, _e(o.name or ''), _e(when),
                rows, _e(_m(o.amount_total or 0)), _e(_m(o.amount_tax or 0)), pays)
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('X-Robots-Tag', 'noindex')])

    # ─── POS summary / analytics (date-range professional report) ─────
    @http.route('/api/mobile/v2/admin/pos/summary', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_summary(self, **kw):
        env = request.env
        if 'pos.order' not in env:
            return ok({'available': False})
        Po = env['pos.order'].sudo()
        dom = [('state', 'in', ['paid', 'done', 'invoiced'])]
        if kw.get('date_from'):
            dom.append(('date_order', '>=', kw.get('date_from')))
        if kw.get('date_to'):
            dom.append(('date_order', '<=', kw.get('date_to') + ' 23:59:59'))
        for _f in ('config_id', 'user_id', 'session_id'):
            if kw.get(_f):
                try:
                    dom.append((_f, '=', int(kw.get(_f))))
                except Exception:
                    pass
        orders = Po.search(dom)
        sales = 0.0
        cost = 0.0
        items = 0
        refunds = 0.0
        prod = {}
        byshop = {}
        bycashier = {}
        for o in orders:
            sales += o.amount_total
            if o.amount_total < 0:
                refunds += o.amount_total
            _sh = o.config_id.name or '-'
            _ca = o.user_id.name or '-'
            byshop[_sh] = byshop.get(_sh, 0) + o.amount_total
            bycashier[_ca] = bycashier.get(_ca, 0) + o.amount_total
            for l in o.lines:
                pv = l.product_id
                e = prod.setdefault(pv.id, {
                    'id': pv.product_tmpl_id.id, 'name': pv.name or '',
                    'qty': 0.0, 'total': 0.0})
                e['qty'] += (l.qty or 0)
                e['total'] += (l.price_subtotal_incl or 0)
                items += abs(int(l.qty or 0))
                cost += _pos_line_cost(l)
        pm = {}
        try:
            pdom = [('pos_order_id', 'in', orders.ids)] if orders else [('id', '=', 0)]
            for p in env['pos.payment'].sudo().search(pdom):
                _k = p.payment_method_id.name or 'Other'
                pm[_k] = pm.get(_k, 0) + p.amount
        except Exception:
            pass

        def _like(subs):
            return round(sum(v for k, v in pm.items()
                             if any(n in (k or '').lower() for n in subs)), 3)
        profit = round(sales - cost, 3)
        top = sorted(prod.values(), key=lambda x: -x['total'])[:20]
        return ok({
            'available': True,
            'orders': len(orders), 'items': items,
            'sales': _money(env, sales), 'sales_raw': round(sales, 3),
            'cost': _money(env, cost), 'profit': _money(env, profit),
            'margin_pct': round((profit / sales * 100), 1) if sales else 0,
            'refunds': _money(env, refunds),
            'cash_total': _money(env, _like(['cash', 'نقد', 'كاش'])),
            'knet_total': _money(env, _like(['card', 'knet', 'k-net', 'كي', 'بطاق', 'شبك'])),
            'payments': [{'method': k, 'amount': _money(env, v),
                          'amount_raw': round(v, 3)}
                         for k, v in sorted(pm.items(), key=lambda x: -x[1])],
            'top_products': [{'id': p['id'], 'name': p['name'],
                              'qty': round(p['qty'], 2),
                              'total': _money(env, p['total'])} for p in top],
            'by_shop': [{'name': k, 'total': _money(env, v)}
                        for k, v in sorted(byshop.items(), key=lambda x: -x[1])],
            'by_cashier': [{'name': k, 'total': _money(env, v)}
                           for k, v in sorted(bycashier.items(), key=lambda x: -x[1])],
        })

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
            o_cost = 0.0
            o_lines = []
            for l in o.lines:
                lc = _pos_line_cost(l)
                o_cost += lc
                o_lines.append({
                    'name': l.product_id.display_name or '',
                    'qty': l.qty,
                    'price_unit': round(l.price_unit, 3),
                    'total': round(l.price_subtotal_incl, 3),
                    'cost': round(lc, 3),
                    'margin': round(l.price_subtotal - lc, 3),
                })
            o_profit = round(o.amount_total - o_cost, 3)
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
                'lines': o_lines[:20],
                'total': _money(env, o.amount_total, o.currency_id),
                'cost': _money(env, o_cost, o.currency_id),
                'profit': _money(env, o_profit, o.currency_id),
                'margin_pct': round((o_profit / o.amount_total * 100), 1)
                if o.amount_total else 0,
                'payments': [{'method': p.payment_method_id.name or '',
                              'amount': round(p.amount, 3)}
                             for p in o.payment_ids],
            })
        return ok({'orders': rows, 'available': True, 'page': page,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── POS report (aggregate KPIs over a date range) ─────────────────
    @http.route('/api/mobile/v2/admin/pos/report', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_pos_report(self, **kw):
        env = request.env
        if 'pos.order' not in env:
            return ok({'available': False})
        # Window: ?days=N (default 30) over date_order. Cap to keep it light.
        try:
            days = min(370, max(1, int(kw.get('days', 30) or 30)))
        except Exception:
            days = 30
        since = datetime.now() - timedelta(days=days)
        Po = env['pos.order'].sudo()
        orders = Po.search([('date_order', '>=',
                             since.strftime('%Y-%m-%d 00:00:00'))])
        sales = cost = refunds = 0.0
        items = 0
        n_sales = n_refunds = 0
        by_pay = {}
        by_cashier = {}
        by_day = {}
        by_product = {}
        for o in orders:
            tot = o.amount_total or 0.0
            sales += tot
            if tot < 0:
                refunds += tot
                n_refunds += 1
            else:
                n_sales += 1
            ocost = 0.0
            for l in o.lines:
                lc = _pos_line_cost(l)
                ocost += lc
                items += abs(int(l.qty or 0))
                pid = l.product_id.id
                bp = by_product.setdefault(pid, {
                    'name': l.product_id.display_name or '',
                    'qty': 0.0, 'sales': 0.0, 'profit': 0.0})
                bp['qty'] += (l.qty or 0)
                bp['sales'] += (l.price_subtotal_incl or 0.0)
                bp['profit'] += (l.price_subtotal or 0.0) - lc
            cost += ocost
            # by payment method
            for p in o.payment_ids:
                nm = p.payment_method_id.name or '—'
                by_pay[nm] = by_pay.get(nm, 0.0) + (p.amount or 0.0)
            # by cashier
            cname = (o.employee_id.name
                     if 'employee_id' in o._fields and o.employee_id
                     else o.user_id.name) or '—'
            c = by_cashier.setdefault(cname, {
                'sales': 0.0, 'profit': 0.0, 'orders': 0})
            c['sales'] += tot
            c['profit'] += tot - ocost
            c['orders'] += 1
            # by day
            day = (o.date_order + timedelta(hours=3)).strftime('%Y-%m-%d') \
                if o.date_order else '—'
            d = by_day.setdefault(day, {'sales': 0.0, 'profit': 0.0})
            d['sales'] += tot
            d['profit'] += tot - ocost
        profit = round(sales - cost, 3)

        def _m(x):
            return _money(env, x)
        top = sorted(by_product.values(), key=lambda r: r['profit'],
                     reverse=True)[:10]
        return ok({
            'available': True, 'days': days,
            'kpi': {
                'sales': _m(sales), 'cost': _m(cost), 'profit': _m(profit),
                'margin_pct': round((profit / sales * 100), 1) if sales else 0,
                'orders': n_sales, 'refunds_count': n_refunds,
                'refunds': _m(refunds), 'items': items,
                'avg_basket': _m(sales / n_sales) if n_sales else _m(0),
            },
            'by_payment': [{'method': k, 'amount': _m(v)['amount']}
                           for k, v in sorted(
                               by_pay.items(), key=lambda x: -x[1])],
            'by_cashier': [{'name': k, 'sales': _m(v['sales'])['amount'],
                            'profit': _m(v['profit'])['amount'],
                            'orders': v['orders']}
                           for k, v in sorted(
                               by_cashier.items(),
                               key=lambda x: -x[1]['sales'])],
            'by_day': [{'day': k, 'sales': _m(v['sales'])['amount'],
                        'profit': _m(v['profit'])['amount']}
                       for k, v in sorted(by_day.items())],
            'top_products': [{'name': p['name'],
                              'qty': round(p['qty'], 2),
                              'sales': _m(p['sales'])['amount'],
                              'profit': _m(p['profit'])['amount']}
                             for p in top],
            'currency': _ccy(env).symbol or 'KD',
        })

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
        # Hide Uellow World (dropship/China) products from admin search unless
        # the admin explicitly picks the China market (country=cn / world=1).
        _ctry = (kw.get('country') or kw.get('market') or '').strip().lower()
        _show_world = (_ctry in ('cn', 'china', 'الصين', 'صين', 'world')
                       or str(kw.get('world') or '').lower() in ('1', 'true', 'yes')
                       or str(kw.get('dropship') or '').lower() in ('1', 'true', 'yes'))
        if not _show_world and 'is_dropship' in env['product.template']._fields:
            dom.append(('is_dropship', '=', False))
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

    # ─── stock: main internal location helper ──────────────────────────
    def _admin_stock_location(self, env):
        """The company's primary on-hand location (WH/Stock)."""
        wh = env['stock.warehouse'].sudo().search(
            [('company_id', '=', env.company.id)], limit=1) \
            or env['stock.warehouse'].sudo().search([], limit=1)
        if wh and wh.lot_stock_id:
            return wh.lot_stock_id
        return env['stock.location'].sudo().search(
            [('usage', '=', 'internal')], order='id', limit=1)

    # ─── stock ledger: in (purchases) / out (sales) / on-hand ───────────
    @http.route('/api/mobile/v2/admin/product/<int:tmpl_id>/stock',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_product_stock(self, tmpl_id, **kw):
        """Per-product inventory ledger so the admin can verify the real
        on-hand count: total received (purchases/in), total shipped (sales/
        out), current on-hand, the raw move history, and every manual
        adjustment with its reason."""
        env = request.env
        t = env['product.template'].sudo().browse(tmpl_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Product not found', status=404)
        try:
            limit = max(10, min(200, int(kw.get('limit') or 60)))
        except Exception:
            limit = 60
        variants = t.product_variant_ids
        vids = variants.ids

        ML = env['stock.move.line'].sudo()
        lines = ML.search(
            [('product_id', 'in', vids), ('state', '=', 'done')],
            order='date desc, id desc', limit=limit)

        def _u(loc):
            return (loc.usage or '') if loc else ''

        total_in = total_out = 0.0
        history = []
        for ml in lines:
            qty = float(ml.quantity or 0.0)
            if qty <= 0:
                continue
            su, du = _u(ml.location_id), _u(ml.location_dest_id)
            if du == 'internal' and su != 'internal':
                direction, signed = 'in', qty
            elif su == 'internal' and du != 'internal':
                direction, signed = 'out', -qty
            else:
                continue  # internal transfer — no net on-hand change
            partner = ml.picking_id.partner_id.name \
                if ml.picking_id and ml.picking_id.partner_id else ''
            history.append({
                'date': ml.date.strftime('%Y-%m-%d %H:%M') if ml.date else '',
                'ref': ml.reference or (ml.picking_id.name
                                        if ml.picking_id else '') or '',
                'qty': round(signed, 2),
                'direction': direction,
                'from': ml.location_id.display_name if ml.location_id else '',
                'to': ml.location_dest_id.display_name
                if ml.location_dest_id else '',
                'partner': partner,
                'variant': ml.product_id.default_code
                or ml.product_id.display_name or '',
            })

        # true lifetime totals (unbounded by the display limit)
        all_lines = ML.search(
            [('product_id', 'in', vids), ('state', '=', 'done')])
        for ml in all_lines:
            qty = float(ml.quantity or 0.0)
            if qty <= 0:
                continue
            su, du = _u(ml.location_id), _u(ml.location_dest_id)
            if du == 'internal' and su != 'internal':
                total_in += qty
            elif su == 'internal' and du != 'internal':
                total_out += qty

        # manual adjustments (with reasons)
        Adj = env['uellow.stock.adjust'].sudo()
        adjustments = [{
            'date': a.create_date.strftime('%Y-%m-%d %H:%M')
            if a.create_date else '',
            'before': round(a.qty_before, 2),
            'after': round(a.qty_after, 2),
            'delta': round(a.delta, 2),
            'reason': a.reason or '',
            'by': a.user_id.name or '',
            'variant': a.product_id.default_code
            or a.product_id.display_name or '',
        } for a in Adj.search([('template_id', '=', t.id)], limit=limit)]

        per_variant = [{
            'id': v.id,
            'attrs': ', '.join(
                v.product_template_attribute_value_ids.mapped('name')) or '',
            'sku': v.default_code or '',
            'on_hand': round(v.qty_available, 2),
            'forecast': round(v.virtual_available, 2),
            'incoming': round(v.incoming_qty, 2),
            'outgoing': round(v.outgoing_qty, 2),
        } for v in variants]

        on_hand = round(t.qty_available, 2)
        # gap between "what moved" and what's on hand ⇒ explained by
        # manual adjustments / opening balances; surfaced so the admin can spot
        # a suspicious count.
        net_moves = round(total_in - total_out, 2)
        return ok({
            'product': {'id': t.id,
                        'name': t.with_context(lang='en_US').name or t.name,
                        'name_ar': t.with_context(lang='ar_001').name or ''},
            'is_storable': bool(getattr(t, 'is_storable', True)),
            'on_hand': on_hand,
            'forecast': round(t.virtual_available, 2),
            'total_in': round(total_in, 2),
            'total_out': round(total_out, 2),
            'net_moves': net_moves,
            'unexplained': round(on_hand - net_moves, 2),
            'location': (self._admin_stock_location(env).display_name
                         or 'WH/Stock'),
            'uom': t.uom_id.name or '',
            'variants': per_variant,
            'history': history,
            'adjustments': adjustments,
        })

    # ─── stock adjust: set on-hand with a mandatory reason ──────────────
    @http.route('/api/mobile/v2/admin/product/<int:tmpl_id>/stock/adjust',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_product_stock_adjust(self, tmpl_id, **kw):
        """Set a variant's on-hand quantity (inventory adjustment) with a
        REQUIRED reason. Applies via stock.quant inventory mode as SUPERUSER
        (valuation recompute re-checks access) and records an audit row."""
        from odoo import SUPERUSER_ID, api as _api
        # capture the real acting admin (token → partner → user) BEFORE we
        # switch to the SUPERUSER env, so the audit row credits the person,
        # not OdooBot.
        acting_partner = current_partner()
        acting_user = acting_partner.sudo().user_ids[:1] if acting_partner \
            and acting_partner.sudo().user_ids else None
        env = _api.Environment(request.env.cr, SUPERUSER_ID,
                               dict(request.env.context))
        t = env['product.template'].sudo().browse(tmpl_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Product not found', status=404)
        p = get_payload()
        reason = (p.get('reason') or '').strip()
        if not reason:
            return fail('REASON_REQUIRED',
                        'A reason is required / السبب مطلوب', status=400)
        if p.get('qty') is None:
            return fail('QTY_REQUIRED', 'New quantity is required', status=400)
        try:
            new_qty = float(p['qty'])
        except Exception:
            return fail('BAD_QTY', 'Quantity must be a number', status=400)

        # pick the variant (explicit id, else the sole variant)
        variant = None
        if p.get('variant_id'):
            variant = env['product.product'].sudo().browse(
                int(p['variant_id'])).exists()
            if not variant or variant.product_tmpl_id.id != t.id:
                return fail('BAD_VARIANT', 'Variant not found', status=400)
        elif len(t.product_variant_ids) == 1:
            variant = t.product_variant_ids
        else:
            return fail('VARIANT_REQUIRED',
                        'This product has variants — choose one', status=400)

        if not bool(getattr(variant, 'is_storable',
                            getattr(t, 'is_storable', True))):
            return fail('NOT_STORABLE',
                        'Stock is only tracked for storable products',
                        status=400)

        loc = self._admin_stock_location(env)
        if not loc:
            return fail('NO_LOCATION', 'No stock location found', status=400)

        try:
            Quant = env['stock.quant'].sudo().with_context(inventory_mode=True)
            quant = Quant.search([('product_id', '=', variant.id),
                                  ('location_id', '=', loc.id)], limit=1)
            if not quant:
                quant = Quant.create({'product_id': variant.id,
                                      'location_id': loc.id})
            before = float(quant.quantity or 0.0)
            quant.inventory_quantity = new_qty
            quant.action_apply_inventory()
            env['uellow.stock.adjust'].sudo().log(
                variant, loc, before, new_qty, reason,
                user=acting_user or env.user)
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            _logger.warning('admin stock adjust failed', exc_info=True)
            return fail('ADJUST_FAILED', str(e)[:200], status=400)

        return ok({'variant_id': variant.id,
                   'on_hand': round(variant.qty_available, 2),
                   'before': round(before, 2),
                   'after': round(new_qty, 2),
                   'reason': reason})

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
                   'carrier': (getattr(o, 'delivery_carrier_company_id', False)
                               and o.delivery_carrier_company_id.name)
                   or (o.carrier_id.name if o.carrier_id else ''),
                   'driver': getattr(o, 'delivery_driver_id', False)
                   and o.delivery_driver_id.name or ''})

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

    # ─── order: lock / unlock ──────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/lock',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_lock(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        try:
            # Odoo 17/18: `locked` boolean (+ action_lock); fall back to the
            # legacy action_done for older installs.
            if hasattr(o, 'action_lock'):
                o.action_lock()
            elif 'locked' in o._fields:
                o.locked = True
            else:
                o.action_done()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('LOCK_FAILED', str(e)[:200], status=400)
        return ok({'locked': bool(getattr(o, 'locked', True))})

    @http.route('/api/mobile/v2/admin/order/<int:order_id>/unlock',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_unlock(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        try:
            if hasattr(o, 'action_unlock'):
                o.action_unlock()
            elif 'locked' in o._fields:
                o.locked = False
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('UNLOCK_FAILED', str(e)[:200], status=400)
        return ok({'locked': bool(getattr(o, 'locked', False))})

    # ─── order: create + post the customer invoice ─────────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/invoice',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_invoice(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        if o.state not in ('sale', 'done'):
            return fail('NOT_CONFIRMED',
                        'Confirm the order before invoicing', 400)
        try:
            # Reuse an existing draft invoice, else create one, then post.
            invs = o.invoice_ids.filtered(lambda i: i.state == 'draft')
            if not invs:
                invs = o._create_invoices()
            invs.action_post()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('INVOICE_FAILED', str(e)[:200], status=400)
        return ok({'invoices': [{'id': i.id, 'name': i.name or '/',
                                 'state': i.state,
                                 'payment_state': i.payment_state or '',
                                 'amount': round(i.amount_total, 3)}
                                for i in o.invoice_ids],
                   'invoice_status': o.invoice_status or ''})

    # ─── order: validate the delivery (set picking done) ───────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/deliver',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_deliver(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        pickings = o.picking_ids.filtered(
            lambda pk: pk.state not in ('done', 'cancel'))
        if not pickings:
            return ok({'delivered': True, 'already': True})
        try:
            for pk in pickings:
                # Force-fill done quantities so validation never opens a
                # back-order/immediate-transfer wizard in this headless path.
                for ml in pk.move_ids:
                    try:
                        ml.quantity = ml.product_uom_qty
                        if 'picked' in ml._fields:
                            ml.picked = True
                    except Exception:
                        pass
                res = pk.button_validate()
                # A returned wizard action means a back-order prompt — accept
                # it (create the back-order) so the present qty is delivered.
                if isinstance(res, dict) and res.get('res_model') == \
                        'stock.backorder.confirmation':
                    wiz = env['stock.backorder.confirmation'].with_context(
                        res.get('context') or {}).create({
                            'pick_ids': [(6, 0, pickings.ids)]})
                    wiz.process()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('DELIVER_FAILED', str(e)[:200], status=400)
        return ok({'pickings': [{'id': pk.id, 'name': pk.name or '',
                                 'state': pk.state} for pk in o.picking_ids]})

    # ─── order: register a payment on the posted invoice ───────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/register-payment',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_register_payment(self, order_id, **kw):
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        invs = o.invoice_ids.filtered(
            lambda i: i.state == 'posted'
            and i.payment_state in ('not_paid', 'partial'))
        if not invs:
            return fail('NOTHING_DUE',
                        'No posted unpaid invoice to pay', 400)
        p = get_payload()
        try:
            ctx = {'active_model': 'account.move',
                   'active_ids': invs.ids}
            wiz_vals = {}
            if p.get('journal_id'):
                wiz_vals['journal_id'] = int(p['journal_id'])
            if p.get('amount'):
                wiz_vals['amount'] = float(p['amount'])
            wiz = env['account.payment.register'].with_context(
                ctx).create(wiz_vals)
            wiz.action_create_payments()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('PAYMENT_FAILED', str(e)[:200], status=400)
        return ok({'invoices': [{'id': i.id, 'name': i.name or '/',
                                 'state': i.state,
                                 'payment_state': i.payment_state or '',
                                 'amount': round(i.amount_total, 3)}
                                for i in o.invoice_ids]})

    # ─── order: reconcile an online (UPayments) payment ────────────────
    @http.route('/api/mobile/v2/admin/order/<int:order_id>/verify-payment',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_order_verify_payment(self, order_id, **kw):
        """Query UPayments for the live charge status and capture the order if
        the customer actually paid (heals a missed capture webhook)."""
        env = _su_env()
        o = env['sale.order'].browse(order_id).exists()
        if not o:
            return fail('NOT_FOUND', 'Order not found', status=404)
        if not hasattr(o, '_upayments_verify_status'):
            return fail('UNSUPPORTED', 'UPayments not installed', 400)
        try:
            paid = o._upayments_verify_status()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('VERIFY_FAILED', str(e)[:200], status=400)
        return ok({'paid': bool(paid), 'state': o.state,
                   'track_id': getattr(o, 'upayments_track_id', '') or ''})

    # ─── customer activity (journey) ───────────────────────────────────
    def _activity_row(self, a):
        when = a.event_time or a.create_date
        ref = None
        if a.ref_model and a.ref_id:
            ref = {'model': a.ref_model, 'id': a.ref_id}
        return {
            'id': a.id,
            'when': when and (when + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M:%S') or '',
            'event': a.event or '',
            'screen': a.screen or '',
            'label': a.label or '',
            'ref': ref,
            'duration_ms': a.duration_ms or 0,
            'platform': a.platform or '',
            'app_version': a.app_version or '',
            'device': a.device or '',
            'customer': {'id': a.partner_id.id,
                         'name': a.partner_id.name or 'Guest'}
            if a.partner_id else {'id': 0, 'name': 'Guest'},
        }

    @http.route('/api/mobile/v2/admin/activity/recent', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_activity_recent(self, **kw):
        env = request.env
        if env.get('uellow.customer.activity') is None:
            return ok({'activities': [], 'available': False})
        A = env['uellow.customer.activity'].sudo()
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(100, max(10, int(kw.get('per_page', 50) or 50)))
        dom = []
        if kw.get('partner_id'):
            dom.append(('partner_id', '=', int(kw['partner_id'])))
        if kw.get('event'):
            dom.append(('event', '=', kw['event']))
        if (kw.get('q') or '').strip():
            q = kw['q'].strip()
            dom += ['|', '|', ('screen', 'ilike', q),
                    ('label', 'ilike', q), ('partner_id.name', 'ilike', q)]
        total = A.search_count(dom)
        rows = A.search(dom, order='id desc', limit=per,
                        offset=(page - 1) * per)
        return ok({'activities': [self._activity_row(a) for a in rows],
                   'available': True, 'page': page, 'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    @http.route('/api/mobile/v2/admin/customer/<int:partner_id>/activity',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_customer_activity(self, partner_id, **kw):
        env = request.env
        if env.get('uellow.customer.activity') is None:
            return ok({'timeline': [], 'available': False})
        A = env['uellow.customer.activity'].sudo()
        p = env['res.partner'].sudo().browse(partner_id)
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(200, max(20, int(kw.get('per_page', 80) or 80)))
        dom = [('partner_id', '=', partner_id)]
        total = A.search_count(dom)
        rows = A.search(dom, order='id desc', limit=per,
                        offset=(page - 1) * per)
        # summary
        first = A.search(dom, order='id asc', limit=1)
        last = A.search(dom, order='id desc', limit=1)
        sessions = len(set(A.search(dom).mapped('session_token')))

        def _fmt(rec):
            w = rec and (rec.event_time or rec.create_date)
            return w and (w + timedelta(hours=3)).strftime(
                '%Y-%m-%d %H:%M') or ''
        # top screens (group manually, capped scan)
        scr = {}
        for a in A.search([('partner_id', '=', partner_id),
                           ('event', 'in', ('screen_view', 'screen'))],
                          limit=2000):
            if a.screen:
                scr[a.screen] = scr.get(a.screen, 0) + 1
        top = sorted(scr.items(), key=lambda x: -x[1])[:8]
        return ok({
            'available': True,
            'customer': {'id': p.id, 'name': p.name or '',
                         'phone': p.phone or p.mobile or '',
                         'email': p.email or ''},
            'summary': {
                'events': total, 'sessions': sessions,
                'first_seen': _fmt(first), 'last_seen': _fmt(last),
                'top_screens': [{'screen': s, 'count': c} for s, c in top],
            },
            'timeline': [self._activity_row(a) for a in rows],
            'page': page, 'pages': (total + per - 1) // per if per else 1,
            'total': total,
        })

    # ══════════════════════════════════════════════════════════════════
    # Helpdesk — support-ticket manager for the in-app admin console
    # (v2.2.x). Endpoints:
    #   GET  /admin/helpdesk/meta            — KPIs + teams + stages (filters)
    #   GET  /admin/helpdesk/tickets         — paginated list (search+filters)
    #   GET  /admin/helpdesk/ticket/<id>     — full detail + chatter thread
    #   POST /admin/helpdesk/ticket/<id>/reply   — public reply or internal note
    #   POST /admin/helpdesk/ticket/<id>/stage   — move stage / close
    #   POST /admin/helpdesk/ticket/<id>/assign  — (re)assign to a user
    # ══════════════════════════════════════════════════════════════════

    # priority on helpdesk.ticket is a selection '0'..'3'; bilingual labels.
    _HD_PRIORITY = {
        '0': {'en': 'Low', 'ar': 'منخفضة'},
        '1': {'en': 'Medium', 'ar': 'متوسطة'},
        '2': {'en': 'High', 'ar': 'عالية'},
        '3': {'en': 'Urgent', 'ar': 'عاجلة'},
    }
    _HD_KANBAN = {
        'normal': {'en': 'In Progress', 'ar': 'قيد التنفيذ'},
        'done':   {'en': 'Ready', 'ar': 'جاهزة'},
        'blocked': {'en': 'Blocked', 'ar': 'متوقفة'},
    }

    def _hd_ticket_row(self, t):
        when = t.create_date and (t.create_date + timedelta(hours=3)) or None
        return {
            'id': t.id,
            'ref': t.ticket_ref or str(t.id),
            'subject': t.name or '',
            'customer': t.partner_name or (t.partner_id.name if t.partner_id
                                           else '') or '',
            'phone': (t.partner_id.phone or t.partner_id.mobile or '')
            if t.partner_id else '',
            'team': t.team_id.name or '',
            'team_id': t.team_id.id or None,
            'stage': t.stage_id.name or '',
            'stage_id': t.stage_id.id or None,
            'closed': bool(t.stage_id.fold),
            'priority': t.priority or '0',
            'priority_label': self._HD_PRIORITY.get(t.priority or '0'),
            'assignee': t.user_id.name or '',
            'assignee_id': t.user_id.id or None,
            'created': when and when.strftime('%Y-%m-%d %H:%M') or '',
        }

    @http.route('/api/mobile/v2/admin/helpdesk/meta', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_meta(self, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        Ticket = Ticket.sudo()
        Stage = env['helpdesk.stage'].sudo()
        Team = env['helpdesk.team'].sudo()
        stages = Stage.search([], order='sequence, id')
        # KPIs — open = unfolded stages, today = created since midnight.
        open_stage_ids = stages.filtered(lambda s: not s.fold).ids
        now = datetime.now()
        today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        kpi = {
            'total': Ticket.search_count([]),
            'open': Ticket.search_count(
                [('stage_id', 'in', open_stage_ids)]) if open_stage_ids else 0,
            'unassigned': Ticket.search_count(
                [('user_id', '=', False),
                 ('stage_id', 'in', open_stage_ids)]) if open_stage_ids else 0,
            'today': Ticket.search_count(
                [('create_date', '>=', today0.strftime('%Y-%m-%d %H:%M:%S'))]),
            'high_priority': Ticket.search_count(
                [('priority', 'in', ('2', '3')),
                 ('stage_id', 'in', open_stage_ids)]) if open_stage_ids else 0,
        }
        # per-stage live counts (for the filter chips).
        stage_list = [{
            'id': s.id, 'name': s.name, 'fold': bool(s.fold),
            'count': Ticket.search_count([('stage_id', '=', s.id)]),
        } for s in stages]
        team_list = [{
            'id': tm.id, 'name': tm.name,
            'count': Ticket.search_count([('team_id', '=', tm.id)]),
        } for tm in Team.search([('active', '=', True)])]
        return ok({
            'kpi': kpi,
            'stages': stage_list,
            'teams': team_list,
            'priorities': [{'key': k, 'label': v}
                           for k, v in sorted(self._HD_PRIORITY.items())],
            'status_filters': [
                {'key': 'open',   'en': 'Open',   'ar': 'مفتوحة'},
                {'key': 'closed', 'en': 'Closed', 'ar': 'مغلقة'},
                {'key': 'all',    'en': 'All',    'ar': 'الكل'},
            ],
        })

    @http.route('/api/mobile/v2/admin/helpdesk/tickets', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_tickets(self, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        Ticket = Ticket.sudo()
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        dom = []
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', '|', '|',
                    ('name', 'ilike', q),
                    ('ticket_ref', 'ilike', q),
                    ('partner_name', 'ilike', q),
                    ('partner_id.phone', 'ilike', q)]
        if kw.get('stage_id'):
            try:
                dom.append(('stage_id', '=', int(kw['stage_id'])))
            except Exception:
                pass
        if kw.get('team_id'):
            try:
                dom.append(('team_id', '=', int(kw['team_id'])))
            except Exception:
                pass
        if kw.get('priority') in ('0', '1', '2', '3'):
            dom.append(('priority', '=', kw['priority']))
        if kw.get('unassigned') in ('1', 'true', 'True'):
            dom.append(('user_id', '=', False))
        status = (kw.get('status') or 'open').strip()
        if status in ('open', 'closed'):
            folded = env['helpdesk.stage'].sudo().search(
                [('fold', '=', True)]).ids
            if status == 'open':
                dom.append(('stage_id', 'not in', folded))
            else:
                dom.append(('stage_id', 'in', folded))
        total = Ticket.search_count(dom)
        tickets = Ticket.search(dom, order='priority desc, create_date desc',
                                limit=per, offset=(page - 1) * per)
        rows = [self._hd_ticket_row(t) for t in tickets]
        return ok({'tickets': rows, 'page': page, 'per_page': per,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    @http.route('/api/mobile/v2/admin/helpdesk/ticket/<int:ticket_id>',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_ticket_detail(self, ticket_id, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        t = Ticket.sudo().browse(ticket_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Ticket not found', status=404)
        data = self._hd_ticket_row(t)
        data['description'] = t.description or ''
        data['kanban_state'] = t.kanban_state or 'normal'
        data['kanban_label'] = self._HD_KANBAN.get(
            t.kanban_state or 'normal')
        data['email'] = (t.partner_email
                         or (t.partner_id.email if t.partner_id else '') or '')
        data['tags'] = [tg.name for tg in t.tag_ids]
        data['sla_deadline'] = (t.sla_deadline.strftime('%Y-%m-%d %H:%M')
                                if t.sla_deadline else '')
        # linked order (if the ticket came from a mobile order)
        if t.sale_order_id:
            data['order'] = {'id': t.sale_order_id.id,
                             'name': t.sale_order_id.name or ''}
        # chatter — newest last, customer messages + internal notes only.
        thread = []
        for m in t.message_ids.sorted(key=lambda x: x.id):
            if m.message_type not in ('comment', 'email'):
                continue
            body = (m.body or '').strip()
            if not body:
                continue
            when = m.date and (m.date + timedelta(hours=3)) or None
            # `is_internal` is often left NULL by message_post; the reliable
            # signal for a private note is the subtype's `internal` flag.
            is_note = bool(m.is_internal) or bool(
                m.subtype_id and m.subtype_id.internal)
            thread.append({
                'id': m.id,
                'author': m.author_id.name or (m.email_from or 'System'),
                'body': body,
                'is_note': is_note,
                'date': when and when.strftime('%Y-%m-%d %H:%M') or '',
            })
        data['thread'] = thread
        return ok(data)

    @http.route('/api/mobile/v2/admin/helpdesk/ticket/<int:ticket_id>/reply',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_ticket_reply(self, ticket_id, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        t = Ticket.sudo().browse(ticket_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Ticket not found', status=404)
        p = get_payload()
        body = (p.get('body') or '').strip()
        if not body:
            return fail('EMPTY', 'Message body is required', status=400)
        # internal=True → private note (agents only); else a customer reply
        # that emails the ticket followers via the discussion subtype.
        internal = bool(p.get('internal'))
        author = current_partner()
        try:
            t.message_post(
                body=body,
                author_id=author.id if author else False,
                message_type='comment',
                subtype_xmlid='mail.mt_note' if internal else 'mail.mt_comment')
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('REPLY_FAILED', str(e)[:200], status=400)
        return ok({'posted': True, 'internal': internal})

    @http.route('/api/mobile/v2/admin/helpdesk/ticket/<int:ticket_id>/stage',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_ticket_stage(self, ticket_id, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        t = Ticket.sudo().browse(ticket_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Ticket not found', status=404)
        p = get_payload()
        stage_id = int(p.get('stage_id') or 0)
        if not stage_id:
            return fail('BAD_REQUEST', 'stage_id is required', status=400)
        stage = env['helpdesk.stage'].sudo().browse(stage_id).exists()
        if not stage:
            return fail('NOT_FOUND', 'Stage not found', status=404)
        try:
            t.write({'stage_id': stage.id})
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('STAGE_FAILED', str(e)[:200], status=400)
        return ok({'stage_id': stage.id, 'stage': stage.name,
                   'closed': bool(stage.fold)})

    @http.route('/api/mobile/v2/admin/helpdesk/ticket/<int:ticket_id>/assign',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_ticket_assign(self, ticket_id, **kw):
        env = request.env
        Ticket = env.get('helpdesk.ticket')
        if Ticket is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        t = Ticket.sudo().browse(ticket_id).exists()
        if not t:
            return fail('NOT_FOUND', 'Ticket not found', status=404)
        p = get_payload()
        # user_id=0/false → unassign; 'me' → assign to the admin's own user.
        raw = p.get('user_id')
        if raw in ('me', 'self'):
            partner = current_partner()
            usr = partner.sudo().user_ids[:1] if partner else None
            uid = usr.id if usr else 0
        else:
            try:
                uid = int(raw or 0)
            except Exception:
                uid = 0
        try:
            if uid:
                if not env['res.users'].sudo().browse(uid).exists():
                    return fail('NOT_FOUND', 'User not found', status=404)
                t.write({'user_id': uid})
            else:
                t.write({'user_id': False})
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('ASSIGN_FAILED', str(e)[:200], status=400)
        return ok({'assignee_id': t.user_id.id or None,
                   'assignee': t.user_id.name or ''})

    @http.route('/api/mobile/v2/admin/helpdesk/agents', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_helpdesk_agents(self, **kw):
        """Assignable users — helpdesk team members, else internal users."""
        env = request.env
        if env.get('helpdesk.ticket') is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', status=503)
        members = env['res.users'].sudo().browse([])
        Team = env['helpdesk.team'].sudo()
        for tm in Team.search([('active', '=', True)]):
            if 'member_ids' in tm._fields:
                members |= tm.member_ids
        if not members:
            members = env['res.users'].sudo().search(
                [('share', '=', False), ('active', '=', True)], limit=80)
        return ok({'agents': [{'id': u.id, 'name': u.name}
                              for u in members]})

    # ═══════════════════════════════════════════════════════════════════
    # PURCHASE (procurement) — RFQs / purchase orders manager
    # ═══════════════════════════════════════════════════════════════════
    _PO_STATE_LABELS = {
        'draft': ('RFQ', 'طلب عرض سعر'),
        'sent': ('RFQ Sent', 'تم إرسال الطلب'),
        'to approve': ('To Approve', 'بانتظار الموافقة'),
        'purchase': ('Purchase Order', 'أمر شراء'),
        'done': ('Locked', 'مغلق'),
        'cancel': ('Cancelled', 'ملغي'),
    }

    def _po_receipt_status(self, po):
        """('pending'|'partial'|'full'|'none') for the incoming pickings."""
        picks = po.picking_ids.filtered(
            lambda p: p.picking_type_code == 'incoming'
            and p.state != 'cancel')
        if not picks:
            return 'none'
        states = set(picks.mapped('state'))
        if states == {'done'}:
            return 'full'
        if 'done' in states:
            return 'partial'
        return 'pending'

    # ─── purchase: meta (state counts for filter chips) ────────────────
    @http.route('/api/mobile/v2/admin/purchase/meta', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_meta(self, **kw):
        env = request.env
        PO = env['purchase.order'].sudo()
        counts = {}
        for st in ('draft', 'sent', 'to approve', 'purchase', 'done',
                   'cancel'):
            counts[st] = PO.search_count([('state', '=', st)])
        counts['rfq'] = counts['draft'] + counts['sent']
        counts['all'] = PO.search_count([])
        return ok({'counts': counts})

    # ─── purchase: list ────────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchases', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchases(self, **kw):
        env = request.env
        PO = env['purchase.order'].sudo()
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(40, max(5, int(kw.get('per_page', 20) or 20)))
        dom = []
        q = (kw.get('q') or '').strip()
        if q:
            dom += ['|', '|', ('name', 'ilike', q),
                    ('partner_id.name', 'ilike', q),
                    ('partner_ref', 'ilike', q)]
        state = (kw.get('state') or '').strip()
        if state == 'rfq':
            dom.append(('state', 'in', ('draft', 'sent')))
        elif state == 'to_approve':
            dom.append(('state', '=', 'to approve'))
        elif state == 'purchase':
            dom.append(('state', 'in', ('purchase', 'done')))
        elif state == 'cancel':
            dom.append(('state', '=', 'cancel'))
        elif state == 'to_receive':
            dom.append(('state', 'in', ('purchase', 'done')))
            # narrowed in Python below by receipt status
        elif state == 'to_bill':
            dom.append(('invoice_status', '=', 'to invoice'))
        total = PO.search_count(dom)
        pos = PO.search(dom, order='date_order desc',
                        limit=per, offset=(page - 1) * per)
        rows = []
        for po in pos:
            recv = self._po_receipt_status(po)
            if state == 'to_receive' and recv in ('full', 'none'):
                continue
            lbl = self._PO_STATE_LABELS.get(po.state, (po.state, po.state))
            rows.append({
                'id': po.id, 'name': po.name,
                'date': po.date_order and
                (po.date_order + timedelta(hours=3))
                .strftime('%Y-%m-%d %H:%M') or '',
                'vendor': po.partner_id.name or '',
                'vendor_ref': po.partner_ref or '',
                'state': po.state,
                'state_label': lbl[0], 'state_label_ar': lbl[1],
                'receipt_status': recv,
                'invoice_status': po.invoice_status or '',
                'items': int(sum(l.product_qty for l in po.order_line)),
                'total': _money(env, po.amount_total, po.currency_id),
            })
        return ok({'purchases': rows, 'page': page, 'per_page': per,
                   'total': total,
                   'pages': (total + per - 1) // per if per else 1})

    # ─── purchase: detail ──────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_detail(self, po_id, **kw):
        env = request.env
        po = env['purchase.order'].sudo().browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        lines = []
        for l in po.order_line:
            p = l.product_id
            lines.append({
                'id': l.id,
                'product_id': p.id if p else 0,
                'name': l.name or (p.display_name if p else ''),
                'image': p and img_url('product.product', p.id, 'image_128',
                                       unique=p.write_date) or '',
                'qty': l.product_qty,
                'received': getattr(l, 'qty_received', 0.0) or 0.0,
                'billed': getattr(l, 'qty_invoiced', 0.0) or 0.0,
                'price_unit': round(l.price_unit, 3),
                'total': round(l.price_total, 3),
            })
        pickings = [{
            'id': pk.id, 'name': pk.name or '',
            'state': pk.state,
            'type': pk.picking_type_code or '',
        } for pk in po.picking_ids]
        bills = [{
            'id': b.id, 'name': b.name or '/',
            'state': b.state, 'payment_state': b.payment_state or '',
            'amount': round(b.amount_total, 3),
        } for b in po.invoice_ids]
        recv = self._po_receipt_status(po)
        lbl = self._PO_STATE_LABELS.get(po.state, (po.state, po.state))
        confirmed = po.state in ('purchase', 'done')
        data = {
            'id': po.id, 'name': po.name, 'state': po.state,
            'state_label': lbl[0], 'state_label_ar': lbl[1],
            'date': po.date_order and
            (po.date_order + timedelta(hours=3))
            .strftime('%Y-%m-%d %H:%M') or '',
            'date_approve': po.date_approve and
            po.date_approve.strftime('%Y-%m-%d') or '',
            'receipt_status': recv,
            'invoice_status': po.invoice_status or '',
            'vendor': {
                'id': po.partner_id.id,
                'name': po.partner_id.name or '',
                'phone': po.partner_id.phone or po.partner_id.mobile or '',
                'email': po.partner_id.email or '',
                'ref': po.partner_ref or '',
            },
            'lines': lines,
            'pickings': pickings,
            'bills': bills,
            'amounts': {
                'untaxed': _money(env, po.amount_untaxed, po.currency_id),
                'tax': _money(env, po.amount_tax, po.currency_id),
                'total': _money(env, po.amount_total, po.currency_id),
            },
            'can': {
                'confirm': po.state in ('draft', 'sent', 'to approve'),
                'cancel': po.state not in ('cancel', 'done'),
                'receive': confirmed and recv in ('pending', 'partial'),
                'bill': confirmed and po.invoice_status == 'to invoice',
                'edit': po.state in ('draft', 'sent'),
                'pay': bool(po.invoice_ids.filtered(
                    lambda b: b.state == 'posted'
                    and b.payment_state in ('not_paid', 'partial'))),
                # Vendor can always be (re)sent the document while it is not
                # cancelled — email needs an address, whatsapp a phone.
                'send': po.state != 'cancel',
                'send_email': po.state != 'cancel' and bool(po.partner_id.email),
                'send_whatsapp': po.state != 'cancel' and bool(
                    po.partner_id.phone or po.partner_id.mobile),
            },
            'note': po.notes and str(po.notes)[:500] or '',
        }
        return ok(data)

    # ─── purchase: send to vendor (Email / WhatsApp) ───────────────────
    def _po_report_ref(self, po):
        """RFQ → quotation report; confirmed PO → purchase-order report."""
        if po.state in ('purchase', 'done'):
            return 'purchase.action_report_purchase_order'
        return 'purchase.report_purchase_quotation'

    def _po_pdf_attachment(self, env, po):
        """Render the PO/RFQ PDF and store it as a public-token attachment.
        Returns (attachment, public_download_url)."""
        ref = self._po_report_ref(po)
        report = env.ref(ref)
        pdf, _ctype = report.sudo()._render_qweb_pdf(ref, po.ids)
        fname = '%s.pdf' % (po.name or 'PO').replace('/', '_')
        att = env['ir.attachment'].sudo().create({
            'name': fname,
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'res_model': 'purchase.order',
            'res_id': po.id,
            'mimetype': 'application/pdf',
        })
        att.generate_access_token()
        base = env['ir.config_parameter'].sudo().get_param(
            'web.base.url') or ''
        url = '%s/web/content/%s?access_token=%s&download=true&filename=%s' % (
            base, att.id, att.access_token, urllib.parse.quote(fname))
        return att, url

    def _wa_phone(self, raw):
        """Normalise a vendor phone to wa.me digits (Kuwait default +965)."""
        digits = ''.join(ch for ch in (raw or '') if ch.isdigit())
        if not digits:
            return ''
        if len(digits) == 8:          # bare Kuwait local number
            digits = '965' + digits
        return digits

    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/send',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_send(self, po_id, **kw):
        """Send the RFQ/PO to the vendor via Email or WhatsApp.

        Payload: {channel: 'email'|'whatsapp'}.
        - email    : sends the purchase email template (PDF attached) to the
                     vendor and flips a draft RFQ to 'sent'.
        - whatsapp : renders the PDF as a public-token link, builds a wa.me
                     deep link with a bilingual message + PDF link, flips a
                     draft RFQ to 'sent', and returns the link for the app to
                     open. (No WhatsApp Business API needed.)
        """
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)

        p = get_payload()
        channel = (p.get('channel') or kw.get('channel') or 'email').strip()
        vendor = po.partner_id

        try:
            if channel == 'email':
                if not vendor.email:
                    return fail('NO_EMAIL',
                                'Vendor has no email address', 400)
                tmpl = env.ref('purchase.email_template_edi_purchase',
                               raise_if_not_found=False)
                if tmpl:
                    tmpl.sudo().send_mail(po.id, force_send=True)
                else:
                    # Fallback: post the PDF as a message to the vendor
                    _att, _url = self._po_pdf_attachment(env, po)
                    po.message_post(
                        body='Purchase order %s' % po.name,
                        partner_ids=[vendor.id],
                        attachment_ids=[_att.id],
                        subtype_xmlid='mail.mt_comment')
                if po.state == 'draft':
                    po.write({'state': 'sent'})
                request.env.cr.commit()
                return ok({'channel': 'email', 'sent': True,
                           'to': vendor.email, 'state': po.state})

            elif channel == 'whatsapp':
                _att, pdf_url = self._po_pdf_attachment(env, po)
                phone = self._wa_phone(vendor.phone or vendor.mobile)
                total = _money(env, po.amount_total, po.currency_id)
                n_items = int(sum(l.product_qty for l in po.order_line))
                # Bilingual vendor message
                msg = (
                    "مرحباً %s،\n"
                    "نرفق لكم طلب الشراء *%s* من Uellow.\n"
                    "عدد الأصناف: %s — الإجمالي: %s\n"
                    "ملف الطلب (PDF): %s\n\n"
                    "Hello %s,\n"
                    "Please find Uellow purchase order *%s*.\n"
                    "Items: %s — Total: %s\n"
                    "Order PDF: %s"
                ) % (vendor.name or '', po.name, n_items, total, pdf_url,
                     vendor.name or '', po.name, n_items, total, pdf_url)
                wa_url = 'https://wa.me/%s?text=%s' % (
                    phone, urllib.parse.quote(msg))
                if po.state == 'draft':
                    po.write({'state': 'sent'})
                po.message_post(
                    body='RFQ/PO sent to vendor via WhatsApp.',
                    subtype_xmlid='mail.mt_note')
                request.env.cr.commit()
                return ok({'channel': 'whatsapp', 'wa_url': wa_url,
                           'pdf_url': pdf_url, 'phone': phone,
                           'state': po.state})

            return fail('BAD_CHANNEL', 'channel must be email or whatsapp', 400)
        except Exception as e:
            request.env.cr.rollback()
            return fail('SEND_FAILED', str(e)[:200], status=400)

    # ─── purchase: confirm (RFQ → PO) ──────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/confirm',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_confirm(self, po_id, **kw):
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        if po.state in ('purchase', 'done'):
            return ok({'state': po.state, 'already': True})
        try:
            po.button_confirm()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CONFIRM_FAILED', str(e)[:200], status=400)
        return ok({'state': po.state})

    # ─── purchase: cancel ──────────────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/cancel',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_cancel(self, po_id, **kw):
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        try:
            po.button_cancel()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CANCEL_FAILED', str(e)[:200], status=400)
        return ok({'state': po.state})

    # ─── purchase: receive (validate incoming pickings) ────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/receive',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_receive(self, po_id, **kw):
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        pickings = po.picking_ids.filtered(
            lambda pk: pk.picking_type_code == 'incoming'
            and pk.state not in ('done', 'cancel'))
        if not pickings:
            return ok({'received': True, 'already': True})
        try:
            for pk in pickings:
                for ml in pk.move_ids:
                    try:
                        ml.quantity = ml.product_uom_qty
                        if 'picked' in ml._fields:
                            ml.picked = True
                    except Exception:
                        pass
                res = pk.button_validate()
                if isinstance(res, dict) and res.get('res_model') == \
                        'stock.backorder.confirmation':
                    wiz = env['stock.backorder.confirmation'].with_context(
                        res.get('context') or {}).create({
                            'pick_ids': [(6, 0, pickings.ids)]})
                    wiz.process()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('RECEIVE_FAILED', str(e)[:200], status=400)
        return ok({'pickings': [{'id': pk.id, 'name': pk.name or '',
                                 'state': pk.state}
                                for pk in po.picking_ids],
                   'receipt_status': self._po_receipt_status(po)})

    # ─── purchase: create + post the vendor bill ───────────────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/bill',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_bill(self, po_id, **kw):
        from odoo import fields as _f
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        if po.state not in ('purchase', 'done'):
            return fail('NOT_CONFIRMED',
                        'Confirm the purchase order before billing', 400)
        try:
            existing = po.invoice_ids.filtered(lambda b: b.state == 'draft')
            if not existing:
                po.action_create_invoice()
                existing = po.invoice_ids.filtered(
                    lambda b: b.state == 'draft')
            today = _f.Date.today()
            for b in existing:
                # Vendor bills need an invoice date + a vendor reference to
                # post; default both so the bill posts in one tap.
                if not b.invoice_date:
                    b.invoice_date = today
                if not b.ref and po.partner_ref:
                    b.ref = po.partner_ref
                b.action_post()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('BILL_FAILED', str(e)[:200], status=400)
        return ok({'bills': [{'id': b.id, 'name': b.name or '/',
                              'state': b.state,
                              'payment_state': b.payment_state or '',
                              'amount': round(b.amount_total, 3)}
                             for b in po.invoice_ids],
                   'invoice_status': po.invoice_status or ''})

    # ─── purchase: register a payment on the posted vendor bill ────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/pay',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_pay(self, po_id, **kw):
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        bills = po.invoice_ids.filtered(
            lambda b: b.state == 'posted'
            and b.payment_state in ('not_paid', 'partial'))
        if not bills:
            return fail('NOTHING_DUE',
                        'No posted unpaid vendor bill to pay', 400)
        p = get_payload()
        try:
            ctx = {'active_model': 'account.move', 'active_ids': bills.ids}
            wiz_vals = {}
            if p.get('journal_id'):
                wiz_vals['journal_id'] = int(p['journal_id'])
            if p.get('amount'):
                wiz_vals['amount'] = float(p['amount'])
            wiz = env['account.payment.register'].with_context(
                ctx).create(wiz_vals)
            wiz.action_create_payments()
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('PAYMENT_FAILED', str(e)[:200], status=400)
        return ok({'bills': [{'id': b.id, 'name': b.name or '/',
                              'state': b.state,
                              'payment_state': b.payment_state or '',
                              'amount': round(b.amount_total, 3)}
                             for b in po.invoice_ids]})

    # ─── purchase: vendor picker (for new RFQ) ─────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/vendors', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_vendors(self, **kw):
        env = request.env
        P = env['res.partner'].sudo()
        q = (kw.get('q') or '').strip()
        dom = [('supplier_rank', '>', 0)]
        if q:
            dom = ['&', ('supplier_rank', '>', 0),
                   '|', '|', ('name', 'ilike', q),
                   ('phone', 'ilike', q), ('email', 'ilike', q)]
        vendors = P.search(dom, order='supplier_rank desc, name', limit=40)
        # If the search found nothing among known suppliers, widen to any
        # company/contact so the admin can still pick a new vendor.
        if not vendors and q:
            vendors = P.search(
                ['|', ('name', 'ilike', q), ('phone', 'ilike', q)],
                order='name', limit=40)
        return ok({'vendors': [{'id': v.id, 'name': v.name or '',
                                'phone': v.phone or v.mobile or '',
                                'city': v.city or ''} for v in vendors]})

    # ─── purchase: product search (for adding lines) ───────────────────
    @http.route('/api/mobile/v2/admin/purchase/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_products(self, **kw):
        env = request.env
        Prod = env['product.product'].sudo()
        q = (kw.get('q') or '').strip()
        dom = [('purchase_ok', '=', True)]
        if q:
            dom = ['&', ('purchase_ok', '=', True),
                   '|', '|', ('name', 'ilike', q),
                   ('default_code', 'ilike', q), ('barcode', 'ilike', q)]
        prods = Prod.search(dom, limit=30)
        return ok({'products': [{
            'id': p.id,
            'name': p.display_name or p.name or '',
            'code': p.default_code or '',
            'cost': round(p.standard_price or 0.0, 3),
            'uom': p.uom_po_id.name or p.uom_id.name or '',
            'image': img_url('product.product', p.id, 'image_128',
                             unique=p.write_date) or '',
        } for p in prods]})

    def _po_write_lines(self, env, po, lines, remove):
        """Apply a line edit/add/remove set to an editable PO. New lines
        (no id) are created so Odoo's computes fill name/price/uom/date;
        an explicit price_unit is then written over the computed one."""
        POL = env['purchase.order.line']
        for rid in (remove or []):
            ln = POL.browse(int(rid)).exists()
            if ln and ln.order_id.id == po.id:
                ln.unlink()
        for l in (lines or []):
            qty = float(l.get('qty') or 0)
            price = l.get('price_unit')
            if l.get('id'):
                ln = POL.browse(int(l['id'])).exists()
                if not ln or ln.order_id.id != po.id:
                    continue
                vals = {}
                if qty > 0:
                    vals['product_qty'] = qty
                if price not in (None, ''):
                    vals['price_unit'] = float(price)
                if vals:
                    ln.write(vals)
            elif l.get('product_id'):
                ln = POL.create({
                    'order_id': po.id,
                    'product_id': int(l['product_id']),
                    'product_qty': qty if qty > 0 else 1.0,
                })
                if price not in (None, ''):
                    ln.price_unit = float(price)

    # ─── purchase: create a new RFQ ────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/create', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_create(self, **kw):
        env = _su_env()
        p = get_payload()
        try:
            vendor_id = int(p.get('vendor_id') or 0)
        except (TypeError, ValueError):
            vendor_id = 0
        if not vendor_id:
            return fail('NO_VENDOR', 'Pick a vendor', status=400)
        lines = p.get('lines') or []
        if not lines:
            return fail('NO_LINES', 'Add at least one product', status=400)
        try:
            po = env['purchase.order'].create({'partner_id': vendor_id})
            self._po_write_lines(env, po, lines, [])
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('CREATE_FAILED', str(e)[:200], status=400)
        return ok({'id': po.id, 'name': po.name, 'state': po.state})

    # ─── purchase: edit lines (qty / price / add / remove) ─────────────
    @http.route('/api/mobile/v2/admin/purchase/<int:po_id>/update-lines',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_update_lines(self, po_id, **kw):
        env = _su_env()
        po = env['purchase.order'].browse(po_id).exists()
        if not po:
            return fail('NOT_FOUND', 'Purchase order not found', status=404)
        if po.state not in ('draft', 'sent'):
            return fail('NOT_EDITABLE',
                        'Only an RFQ (draft) can be edited', status=400)
        p = get_payload()
        try:
            self._po_write_lines(env, po, p.get('lines') or [],
                                 p.get('remove') or [])
            request.env.cr.commit()
        except Exception as e:
            request.env.cr.rollback()
            return fail('UPDATE_FAILED', str(e)[:200], status=400)
        return ok({'id': po.id, 'name': po.name,
                   'total': round(po.amount_total, 3),
                   'lines': len(po.order_line)})

    # ─── purchase: stats summary ───────────────────────────────────────
    @http.route('/api/mobile/v2/admin/purchase/stats', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_purchase_stats(self, **kw):
        env = request.env
        PO = env['purchase.order'].sudo()
        Move = env['account.move'].sudo()
        now = datetime.now() + timedelta(hours=3)
        month_start = now.replace(day=1).strftime('%Y-%m-%d')
        # Spend = posted vendor bills this month (company currency).
        bills = Move.search([('move_type', '=', 'in_invoice'),
                             ('state', '=', 'posted'),
                             ('invoice_date', '>=', month_start)])
        spend = sum(_to_company(env, b.amount_total, b.currency_id)
                    for b in bills)
        # Open purchase value (confirmed, not fully billed).
        open_pos = PO.search([('state', 'in', ('purchase', 'done'))])
        to_receive = sum(1 for po in open_pos
                         if self._po_receipt_status(po) in
                         ('pending', 'partial'))
        to_bill = PO.search_count([('invoice_status', '=', 'to invoice')])
        rfq_count = PO.search_count([('state', 'in', ('draft', 'sent'))])
        # Top vendors by confirmed-PO value over the last 90 days.
        since = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        recent = PO.search([('state', 'in', ('purchase', 'done')),
                            ('date_order', '>=', since)])
        by_vendor = {}
        for po in recent:
            amt = _to_company(env, po.amount_total, po.currency_id)
            key = (po.partner_id.id, po.partner_id.name or '')
            by_vendor[key] = by_vendor.get(key, 0.0) + amt
        top = sorted(by_vendor.items(), key=lambda kv: kv[1],
                     reverse=True)[:5]
        return ok({
            'month_spend': _money(env, spend),
            'rfq_count': rfq_count,
            'to_receive': to_receive,
            'to_bill': to_bill,
            'open_count': len(open_pos),
            'top_vendors': [{'id': k[0], 'name': k[1],
                             'amount': _money(env, v)} for k, v in top],
        })
