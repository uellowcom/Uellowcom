# -*- coding: utf-8 -*-
"""
Affiliate mobile API — /api/mobile/v2/affiliate/*
=================================================
me           GET   dashboard: status, code, tier, balances, progress
apply        POST  request to join the program (pending)
products     GET   sellable products + per-product commission + links
orders       GET/POST  submitted orders (agent-entered)
commissions  GET   ledger
payouts      GET/POST  payout history + new request
leaderboard  GET   monthly top agents (masked names)
/r/<code>    GET   public click-tracking redirect
cart/affiliate POST stamp the current cart with a referral code
"""
from datetime import datetime, timedelta

from odoo import http, fields as ofields
from odoo.http import request

from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
    safe_endpoint, ok, fail, get_payload, get_lang, current_partner,
    require_auth, get_website, paginate, bilingual, img_url,
)


def _my_affiliate(required_state=None):
    partner = current_partner()
    if not partner:
        return None
    Aff = request.env['uellow.affiliate'].sudo()
    aff = Aff.search([('partner_id', '=', partner.id)], limit=1) \
        or Aff.search([('partner_id', '=',
                        partner.commercial_partner_id.id)], limit=1)
    if aff and required_state and aff.state != required_state:
        return None
    return aff or None


def _money(v, cur=None):
    cur = cur or request.env.company.currency_id
    return {'amount': round(v or 0.0, 3), 'currency': cur.name,
            'symbol': cur.symbol or 'KD', 'digits': 3}


def _share_links(aff, product=None):
    base = ''
    try:
        w = get_website()
        base = (w.domain or '').rstrip('/')
        if base and not base.startswith('http'):
            base = 'https://' + base
    except Exception:
        pass
    if not base:
        base = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://uellow.com').rstrip('/')
    if product is not None:
        path = product.website_url or '/shop/%s' % product.id
        web = '%s%s?aff=%s' % (base, path, aff.code)
    else:
        web = '%s?aff=%s' % (base, aff.code)
    return {'web': web, 'short': '%s/aff/%s%s' % (
        base, aff.code, ('/p/%d' % product.id) if product is not None else '')}


class UellowAffiliateAPI(http.Controller):

    # ── dashboard ────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/affiliate/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        aff = _my_affiliate()
        if not aff:
            return ok({'status': 'none'})
        cur = aff.currency_id
        # next-tier progress (30d confirmed sales)
        from ..models.affiliate import TIER_RULES
        since = datetime.utcnow() - timedelta(days=30)
        sales30 = sum(c.base_amount for c in aff.commission_ids
                      if c.state in ('confirmed', 'paid')
                      and c.create_date and c.create_date >= since)
        order = ['bronze', 'silver', 'gold', 'platinum']
        nxt = None
        idx = order.index(aff.tier)
        if idx < len(order) - 1:
            need = TIER_RULES[order[idx + 1]][1]
            nxt = {'tier': order[idx + 1], 'needed': need,
                   'current': round(sales30, 3),
                   'progress': min(1.0, sales30 / need) if need else 1.0}
        # this month numbers
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        month_comm = sum(c.amount for c in aff.commission_ids
                         if c.state in ('confirmed', 'paid')
                         and c.create_date
                         and c.create_date >= month_start)
        return ok({
            'status': aff.state,
            'name': aff.name,
            'code': aff.code,
            'tier': aff.tier,
            'tier_multiplier':
                TIER_RULES.get(aff.tier, (1.0, 0))[0],
            'default_pct': aff.default_commission_pct,
            'pending': _money(aff.pending_amount, cur),
            'available': _money(aff.available_amount, cur),
            'paid': _money(aff.paid_amount, cur),
            'month_commission': _money(month_comm, cur),
            'total_sales': _money(aff.total_sales, cur),
            'order_count': aff.order_count,
            'click_count': aff.click_count,
            'next_tier': nxt,
            'links': _share_links(aff),
            'payout_method': aff.payout_method,
            'min_payout': float(request.env['ir.config_parameter'].sudo()
                                .get_param('uellow_affiliate.min_payout',
                                           '5') or 5),
        })

    @http.route('/api/mobile/v2/affiliate/apply', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def apply(self, **kw):
        partner = current_partner()
        if _my_affiliate():
            return fail('ALREADY', 'You already have an affiliate account',
                        400)
        p = get_payload()
        aff = request.env['uellow.affiliate'].sudo().create({
            'name': (p.get('name') or partner.name or '').strip()
                    or partner.name,
            'partner_id': partner.id,
            'phone': (p.get('phone') or partner.phone or '').strip(),
            'email': partner.email or '',
            'note': (p.get('note') or '').strip(),
        })
        return ok({'status': aff.state, 'code': aff.code})

    # ── sellable products ────────────────────────────────────────────
    @http.route('/api/mobile/v2/affiliate/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def products(self, **kw):
        aff = _my_affiliate('active')
        if not aff:
            return fail('NOT_AFFILIATE', 'Affiliate account required', 403)
        p = get_payload()
        lang = get_lang()
        dom = aff.allowed_product_domain()
        q = (p.get('q') or '').strip()
        if q:
            dom += [('name', 'ilike', q)]
        recs = request.env['product.template'].sudo().search(
            dom, order='create_date desc', limit=400)
        ar = str(lang).startswith('ar')

        def ser(t):
            pct = aff.commission_pct_for(t)
            price = t.list_price or 0.0
            comm = price * pct / 100.0
            links = _share_links(aff, t)
            name = bilingual(t, 'name')
            share_text = (
                '%s\n💰 %s\n🛒 %s' % (
                    name['ar' if ar else 'en'] or name['en'],
                    ('السعر: %.3f د.ك' % price) if ar
                    else ('Price: %.3f KD' % price),
                    links['short'] or links['web'])
            )
            return {
                'id': t.id,
                'name': name,
                'image': img_url('product.template', t.id, 'image_512',
                                 unique=t.write_date),
                'price': _money(price),
                'commission_pct': round(pct, 2),
                'commission_amount': _money(comm),
                'links': links,
                'share_text': share_text,
                'in_stock': bool(t.qty_available > 0
                                 or t.allow_out_of_stock_order)
                            if 'allow_out_of_stock_order' in t._fields
                            else True,
            }

        items, meta = paginate(recs, page=p.get('page', 1),
                               per_page=p.get('per_page', 20),
                               serializer=ser)
        return ok({'products': items}, meta)

    # ── submitted orders ─────────────────────────────────────────────
    @http.route('/api/mobile/v2/affiliate/orders', type='http',
                auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def orders(self, **kw):
        aff = _my_affiliate('active')
        if not aff:
            return fail('NOT_AFFILIATE', 'Affiliate account required', 403)
        if request.httprequest.method == 'GET':
            out = []
            for o in aff.submitted_order_ids:
                so_status = ''
                if o.sale_order_id:
                    so_status = o.sale_order_id.state
                out.append({
                    'id': o.id, 'name': o.name, 'state': o.state,
                    'customer_name': o.customer_name,
                    'customer_phone': o.customer_phone,
                    'total': _money(o.amount_total, o.currency_id),
                    'commission': _money(o.est_commission, o.currency_id),
                    'created': o.create_date.isoformat()
                               if o.create_date else None,
                    'sale_order': so_status,
                    'reject_reason': o.reject_reason or '',
                    'lines': [{
                        'product_id': l.product_id.id,
                        'name': l.product_id.display_name,
                        'qty': l.qty, 'price': l.price_unit,
                        'commission_pct': l.commission_pct,
                    } for l in o.line_ids],
                })
            return ok({'orders': out})

        # POST — create + submit
        p = get_payload()
        name = (p.get('customer_name') or '').strip()
        phone = (p.get('customer_phone') or '').strip()
        lines = p.get('lines') or []
        if not name or not phone or not lines:
            return fail('BAD_REQUEST',
                        'customer_name, customer_phone and lines required')
        Tmpl = request.env['product.template'].sudo()
        allowed = set(Tmpl.search(aff.allowed_product_domain()).ids)
        line_vals = []
        for l in lines:
            tid = int(l.get('product_id') or 0)
            qty = float(l.get('qty') or 1)
            tmpl = Tmpl.browse(tid)
            if not tmpl.exists() or tid not in allowed:
                return fail('NOT_ALLOWED',
                            'Product %s is not in your catalog' % tid, 400)
            variant = tmpl.product_variant_id
            line_vals.append((0, 0, {
                'product_id': variant.id,
                'qty': qty,
                'price_unit': tmpl.list_price,
                'commission_pct': aff.commission_pct_for(tmpl),
            }))
        wid = None
        try:
            wid = get_website().id
        except Exception:
            pass
        order = request.env['uellow.affiliate.order'].sudo().create({
            'affiliate_id': aff.id,
            'customer_name': name,
            'customer_phone': phone,
            'customer_area': (p.get('customer_area') or '').strip(),
            'customer_address': (p.get('customer_address') or '').strip(),
            'customer_note': (p.get('customer_note') or '').strip(),
            'website_id': wid,
            'line_ids': line_vals,
        })
        order.action_submit()
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': order.id, 'name': order.name,
                   'state': order.state,
                   'total': _money(order.amount_total),
                   'commission': _money(order.est_commission)})

    # ── ledger + payouts ─────────────────────────────────────────────
    @http.route('/api/mobile/v2/affiliate/commissions', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def commissions(self, **kw):
        aff = _my_affiliate()
        if not aff:
            return fail('NOT_AFFILIATE', 'Affiliate account required', 403)
        out = [{
            'id': c.id,
            'date': c.create_date.isoformat() if c.create_date else None,
            'order': c.sale_order_id.name if c.sale_order_id else '',
            'source': c.source,
            'base': _money(c.base_amount, c.currency_id),
            'amount': _money(c.amount, c.currency_id),
            'state': c.state,
        } for c in aff.commission_ids]
        return ok({'commissions': out})

    @http.route('/api/mobile/v2/affiliate/payouts', type='http',
                auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def payouts(self, **kw):
        aff = _my_affiliate('active')
        if not aff:
            return fail('NOT_AFFILIATE', 'Affiliate account required', 403)
        if request.httprequest.method == 'GET':
            return ok({'payouts': [{
                'id': p.id, 'name': p.name,
                'amount': _money(p.amount, p.currency_id),
                'method': p.method, 'state': p.state,
                'date': p.create_date.isoformat()
                        if p.create_date else None,
            } for p in aff.payout_ids]})
        p = get_payload()
        amount = float(p.get('amount') or 0)
        method = (p.get('method') or aff.payout_method or 'wallet').strip()
        min_payout = float(request.env['ir.config_parameter'].sudo()
                           .get_param('uellow_affiliate.min_payout', '5')
                           or 5)
        if amount < min_payout:
            return fail('TOO_SMALL',
                        'Minimum payout is %.3f / الحد الأدنى للسحب %.3f'
                        % (min_payout, min_payout), 400)
        if amount > aff.available_amount + 0.0001:
            return fail('INSUFFICIENT',
                        'Amount exceeds your available balance / '
                        'المبلغ أكبر من رصيدك المتاح', 400)
        payout = request.env['uellow.affiliate.payout'].sudo().create({
            'affiliate_id': aff.id,
            'amount': amount,
            'method': method,
            'details': (p.get('details') or aff.payout_details or '')
                       .strip(),
        })
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': payout.id, 'name': payout.name,
                   'state': payout.state})

    # ── leaderboard ──────────────────────────────────────────────────
    @http.route('/api/mobile/v2/affiliate/leaderboard', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def leaderboard(self, **kw):
        me = _my_affiliate()
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        rows = request.env['uellow.affiliate.commission'].sudo().search([
            ('state', 'in', ('confirmed', 'paid')),
            ('create_date', '>=', month_start),
        ])
        totals = {}
        for c in rows:
            totals[c.affiliate_id.id] = \
                totals.get(c.affiliate_id.id, 0.0) + c.amount
        ranked = sorted(totals.items(), key=lambda kv: -kv[1])
        Aff = request.env['uellow.affiliate'].sudo()
        out = []
        my_rank = None
        for i, (aid, amt) in enumerate(ranked):
            a = Aff.browse(aid)
            masked = (a.name or '?')
            if len(masked) > 3:
                masked = masked[:3] + '***'
            if me and aid == me.id:
                my_rank = i + 1
                masked = a.name
            if i < 10:
                out.append({'rank': i + 1, 'name': masked,
                            'tier': a.tier,
                            'amount': _money(amt),
                            'me': bool(me and aid == me.id)})
        return ok({'top': out, 'my_rank': my_rank})

    # ── referral attribution ─────────────────────────────────────────
    @http.route('/api/mobile/v2/cart/affiliate', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def cart_affiliate(self, **kw):
        """Stamp the current cart with a referral code (deep-link path)."""
        from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart \
            import _get_or_create_order
        p = get_payload()
        code = (p.get('code') or '').strip()
        if not code:
            return fail('BAD_REQUEST', 'code required')
        order = _get_or_create_order(create=True)
        done = request.env['sale.order'].sudo() \
            .uellow_attach_affiliate_code(order, code)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'attached': bool(done)})

    # ── public click-tracking redirect: /r/<code>[/p/<id>] ──────────
    @http.route(['/aff/<string:code>', '/aff/<string:code>/p/<int:pid>'],
                type='http', auth='public', website=True, csrf=False)
    def referral_redirect(self, code, pid=None, **kw):
        Aff = request.env['uellow.affiliate'].sudo()
        aff = Aff.search([('code', '=', code.strip().upper()),
                          ('state', '=', 'active')], limit=1)
        target = '/'
        if aff:
            try:
                aff.click_count += 1
                request.env.cr.commit()
            except Exception:
                pass
            if pid:
                t = request.env['product.template'].sudo().browse(pid)
                if t.exists():
                    target = t.website_url or '/'
            sep = '&' if '?' in target else '?'
            target = '%s%saff=%s' % (target, sep, aff.code)
        resp = request.redirect(target)
        if aff:
            # 30-day attribution cookie for the website path
            resp.set_cookie('uellow_aff', aff.code,
                            max_age=30 * 24 * 3600, samesite='Lax')
        return resp
