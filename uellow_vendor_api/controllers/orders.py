# -*- coding: utf-8 -*-
"""Vendor orders — /api/vendor/v1/orders*"""
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price, bilingual, img_url,
)


def _state_label(s):
    return {
        'draft':    {'en': 'Draft',     'ar': 'مسودة'},
        'sent':     {'en': 'Quotation', 'ar': 'عرض سعر'},
        'sale':     {'en': 'Confirmed', 'ar': 'مؤكد'},
        'done':     {'en': 'Done',      'ar': 'مكتمل'},
        'cancel':   {'en': 'Cancelled', 'ar': 'ملغي'},
    }.get(s, {'en': s, 'ar': s})


def _ser_order(o, detail=False):
    out = {
        'id': o.id,
        'name': o.name,
        'state': o.state,
        'state_label': _state_label(o.state),
        'when': (o.date_order or o.create_date).isoformat()
                if (o.date_order or o.create_date) else '',
        'customer': {
            'id': o.partner_id.id,
            'name': o.partner_id.name,
            'phone': o.partner_id.phone or o.partner_id.mobile or '',
            'email': o.partner_id.email or '',
        },
        'amount': fmt_price(o.amount_total, o.currency_id),
        'subtotal': fmt_price(o.amount_untaxed, o.currency_id),
        'shipping': fmt_price(o.amount_delivery or 0, o.currency_id),
        'item_count': len(o.order_line.filtered(lambda l: not l.display_type)),
        'invoice_status': o.invoice_status,
    }
    if detail:
        ship = o.partner_shipping_id or o.partner_id
        out['shipping_address'] = {
            'name': ship.name, 'phone': ship.phone or ship.mobile or '',
            'street': ship.street or '', 'street2': ship.street2 or '',
            'city': ship.city or '', 'country': ship.country_id.name if ship.country_id else '',
        }
        out['items'] = []
        for l in o.order_line.filtered(lambda l: not l.display_type):
            p = l.product_id
            out['items'].append({
                'id': l.id,
                'product_id': p.product_tmpl_id.id,
                'name': bilingual(p.product_tmpl_id, 'name'),
                'qty': l.product_uom_qty,
                'price': fmt_price(l.price_unit, o.currency_id),
                'subtotal': fmt_price(l.price_subtotal, o.currency_id),
                'image_url': img_url('product.product', p.id, 'image_256',
                                     unique=p.write_date),
            })
        out['note'] = o.note or ''
    return out


class VendorOrdersAPI(http.Controller):

    @http.route('/api/vendor/v1/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_orders(self, **kw):
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
        if state == 'new':       domain += [('state', '=', 'sent')]
        elif state == 'pending': domain += [('state', '=', 'draft')]
        elif state == 'active':  domain += [('state', '=', 'sale'),
                                            ('invoice_status', '!=', 'invoiced')]
        elif state == 'completed': domain += [('invoice_status', '=', 'invoiced')]
        elif state == 'cancelled': domain += [('state', '=', 'cancel')]
        if search:
            domain += ['|', ('name', 'ilike', search),
                            ('partner_id.name', 'ilike', search)]
        Order = request.env['sale.order'].sudo()
        total = Order.search_count(domain)
        rows = Order.search(domain, order='id desc',
                            limit=per_page, offset=(page - 1) * per_page)
        return ok([_ser_order(o) for o in rows], meta={
            'page': page, 'per_page': per_page, 'total': total,
            'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/vendor/v1/orders/<int:order_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_detail(self, order_id, **kw):
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        return ok({'order': _ser_order(o, detail=True)})

    @http.route('/api/vendor/v1/orders/<int:order_id>/confirm', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def confirm(self, order_id, **kw):
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.state in ('draft', 'sent'):
            o.action_confirm()
        return ok({'state': o.state})

    @http.route('/api/vendor/v1/orders/<int:order_id>/cancel', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cancel(self, order_id, **kw):
        v = current_vendor()
        p = get_payload()
        reason = (p.get('reason') or 'Vendor cancelled').strip()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.state != 'cancel':
            try:
                o._action_cancel() if hasattr(o, '_action_cancel') else o.action_cancel()
            except Exception:
                o.write({'state': 'cancel'})
            o.message_post(body=f'Vendor cancelled: {reason}')
        return ok({'state': 'cancel'})

    @http.route('/api/vendor/v1/orders/<int:order_id>/ship', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def ship(self, order_id, **kw):
        """Trigger picking validation — confirms vendor packed + shipped."""
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        for pick in o.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            try:
                pick.action_assign()
                for ml in pick.move_ids:
                    ml.quantity = ml.product_uom_qty
                pick.button_validate()
            except Exception as e:
                o.message_post(body=f'Ship failed: {e}')
        o.message_post(body='Vendor marked order as shipped')
        return ok({'shipped': True})
