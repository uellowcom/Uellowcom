# -*- coding: utf-8 -*-
"""Group Lamma «شارك لمّتك» — Flutter app endpoints.

Mirrors the web /lamma/group/* flow but with the app's identity model: each
member is keyed by a device-persistent `token` the app sends in every call
(partner linkage is optional). `pay` funnels the member's items into the app
cart (uellow_mobile_manager order) with the fair share discount applied.
"""
import json
import logging

from odoo import http
from odoo.http import request
from .main import _resolve_units

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return request.make_json_response(data, status=status)


def _body():
    try:
        return json.loads(request.httprequest.get_data() or b'{}')
    except Exception:
        return {}


def _find(code):
    if not code:
        return request.env['uellow.lamma.group'].sudo().browse()
    return request.env['uellow.lamma.group'].sudo().search(
        [('code', '=', str(code).strip().upper())], limit=1)


def _app_partner():
    """The logged-in app customer (for push targeting), else None for guests."""
    try:
        from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import _get_or_create_order
        o = _get_or_create_order(create=False)
        if o and o.partner_id:
            pub = request.env.ref('base.public_partner', raise_if_not_found=False)
            if not pub or o.partner_id.id != pub.id:
                return o.partner_id
    except Exception:
        pass
    return None


def _seed(group, member, ids, vmap):
    units = _resolve_units(ids or [], vmap or {})
    have = set(member.line_ids.mapped('product_tmpl_id').ids)
    Line = request.env['uellow.lamma.group.line'].sudo()
    for u in units:
        if u['tmpl'].id in have:
            continue
        Line.create({'group_id': group.id, 'member_id': member.id,
                     'product_tmpl_id': u['tmpl'].id, 'product_id': u['variant'].id})
        have.add(u['tmpl'].id)


class LammaMobileGroup(http.Controller):

    @http.route('/api/mobile/v2/lamma/group/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def create(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        if not tok:
            return _json({'error': 'no_token'}, status=400)
        Group = request.env['uellow.lamma.group'].sudo()
        partner = _app_partner()
        g = Group.create_group(host_token=tok, host_name=p.get('name'),
                               partner=partner, lamma_type=p.get('type') or 'normal')
        host = g.member_ids.filtered('is_host')[:1]
        if host:
            if partner and not host.partner_id:
                host.partner_id = partner.id
            _seed(g, host, p.get('product_ids'), p.get('variants'))
        return _json(g.to_dict(token=tok, partner=partner))

    @http.route('/api/mobile/v2/lamma/group/state', type='http', auth='public',
                methods=['POST', 'GET', 'OPTIONS'], csrf=False, cors='*')
    def state(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body() if request.httprequest.method == 'POST' else kw
        g = _find(p.get('code'))
        if not g:
            return _json({'error': 'not_found'}, status=404)
        for m in g.member_ids:
            if not m.paid and m.sale_order_id and m.sale_order_id.state in ('sale', 'done'):
                m.paid = True
        return _json(g.to_dict(token=(p.get('token') or '').strip()))

    @http.route('/api/mobile/v2/lamma/group/join', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def join(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        g = _find(p.get('code'))
        if not g:
            return _json({'error': 'not_found'}, status=404)
        if g.state != 'open':
            return _json({'error': g.state}, status=409)
        partner = _app_partner()
        me = g._get_or_create_member(token=tok, name=p.get('name'), partner=partner)
        if partner and not me.partner_id:
            me.partner_id = partner.id
        g._notify('join', actor=me)
        return _json(g.to_dict(token=tok, partner=partner))

    @http.route('/api/mobile/v2/lamma/group/add', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def add(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        g = _find(p.get('code'))
        if not g or g.state != 'open':
            return _json({'error': 'closed'}, status=409)
        partner = _app_partner()
        me = g.member_ids.filtered(lambda m: m.token == tok)[:1] or \
            g._get_or_create_member(token=tok, partner=partner)
        if partner and not me.partner_id:
            me.partner_id = partner.id
        vmap = {str(int(p['product_id'])): int(p['variant_id'])} if p.get('variant_id') else {}
        _seed(g, me, [p.get('product_id')], vmap)
        g._notify('add', actor=me)
        return _json(g.to_dict(token=tok, partner=partner))

    @http.route('/api/mobile/v2/lamma/group/remove', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def remove(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        g = _find(p.get('code'))
        if not g or g.state != 'open':
            return _json({'error': 'closed'}, status=409)
        me = g.member_ids.filtered(lambda m: m.token == tok)[:1]
        if me and p.get('product_id'):
            ln = me.line_ids.filtered(lambda l: l.product_tmpl_id.id == int(p['product_id']))[:1]
            if ln:
                ln.unlink()
        return _json(g.to_dict(token=tok))

    @http.route('/api/mobile/v2/lamma/group/lock', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def lock(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        g = _find(p.get('code'))
        if not g:
            return _json({'error': 'not_found'}, status=404)
        me = g.member_ids.filtered(lambda m: m.token == tok)[:1]
        if not me or not me.is_host:
            return _json({'error': 'not_host'}, status=403)
        if g.state == 'open':
            g.state = 'locked'
            g._notify('lock', actor=me)
        return _json(g.to_dict(token=tok))

    @http.route('/api/mobile/v2/lamma/group/pay', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def pay(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        p = _body()
        tok = (p.get('token') or '').strip()
        g = _find(p.get('code'))
        if not g:
            return _json({'error': 'not_found'}, status=404)
        me = g.member_ids.filtered(lambda m: m.token == tok)[:1]
        if not me or not me.line_ids:
            return _json({'error': 'empty'}, status=400)
        discs = g._member_line_discounts(me)  # {variant_id: pct}, headroom-spread
        try:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import _get_or_create_order
            order = _get_or_create_order(create=True)
            if not order:
                return _json({'error': 'no_order'}, status=500)
            Line = request.env['sale.order.line'].sudo()
            for l in me.line_ids:
                v = l.product_id or l.product_tmpl_id.product_variant_id
                if not v:
                    continue
                line = order.order_line.filtered(
                    lambda ol: ol.product_id == v and not ol.display_type
                    and not getattr(ol, 'is_reward_line', False))[:1]
                if not line:
                    line = Line.create({'order_id': order.id, 'product_id': v.id,
                                        'product_uom_qty': 1})
                line.write({'discount': discs.get(v.id, 0.0), 'is_lamma': False})
            me.sale_order_id = order.id
            return _json({'ok': True, 'order_id': order.id,
                          'cart_token': order.mobile_cart_token or ''})
        except Exception as e:
            _logger.exception('lamma group pay failed: %s', e)
            return _json({'error': 'server'}, status=500)
