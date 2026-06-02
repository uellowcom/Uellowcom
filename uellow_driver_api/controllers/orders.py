# -*- coding: utf-8 -*-
"""Driver orders — /api/driver/v1/orders*

list / detail / pickup / decline / start / confirm / fail / return
"""
import base64
import binascii
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
    bilingual, fmt_price, short_addr, order_payment_method,
    order_status_code, status_label,
)


def _serialize_line(line, detail=False):
    o = line.sale_order_id
    if not o:
        return None
    code = order_status_code(line)
    out = {
        'line_id': line.id,
        'id': o.id,
        'name': o.name,
        'created': (o.create_date or datetime.now()).isoformat(),
        'sequence': line.sequence or 0,
        'customer': {
            'name': o.partner_id.name,
            'phone': o.partner_id.phone or o.partner_id.mobile or '',
            'mobile': o.partner_id.mobile or '',
        },
        'address': {
            'short':  short_addr(o.partner_shipping_id or o.partner_id),
            'street': (o.partner_shipping_id or o.partner_id).street or '',
            'street2':(o.partner_shipping_id or o.partner_id).street2 or '',
            'city':   (o.partner_shipping_id or o.partner_id).city or '',
            'country':(o.partner_shipping_id or o.partner_id).country_id.name
                       if (o.partner_shipping_id or o.partner_id).country_id else '',
            'lat':    getattr(o.partner_shipping_id or o.partner_id, 'partner_latitude', 0),
            'lng':    getattr(o.partner_shipping_id or o.partner_id, 'partner_longitude', 0),
        },
        'total': fmt_price(o.amount_total, o.currency_id),
        'payment_method': order_payment_method(o),
        'pay_link_status': getattr(o, 'pay_link_status', '') or 'none',
        'item_count': len(o.order_line.filtered(lambda l: not l.display_type)),
        'status': code,
        'status_label': status_label(code),
    }
    if detail:
        out['items'] = []
        for sl in o.order_line.filtered(lambda l: not l.display_type):
            p = sl.product_id
            out['items'].append({
                'id': sl.id,
                'name': bilingual(p.product_tmpl_id, 'name'),
                'qty': sl.product_uom_qty,
                'price': fmt_price(sl.price_unit, o.currency_id),
                'subtotal': fmt_price(sl.price_subtotal, o.currency_id),
                'image_url': f'/web/image/product.product/{p.id}/image_256'
                              f'?unique={p.write_date}',
            })
        out['notes'] = line.notes or ''
        out['failure_reason'] = line.failure_reason or ''
        out['proof_image_url'] = (
            f'/web/image/delivery.trip.line/{line.id}/proof_image'
            f'?unique={line.write_date}') if line.proof_image else None
        out['signature_url'] = (
            f'/web/image/delivery.trip.line/{line.id}/proof_signature'
            f'?unique={line.write_date}') if line.proof_signature else None
        # Status timeline based on the trip line transitions
        ts = []
        # Odoo 18 dropped sale.order.confirmation_date; date_order is the
        # closest equivalent (it gets stamped to confirmation time on
        # action_confirm). Fall back to create_date for drafts.
        ts.append(('confirmed', o.date_order or o.create_date))
        if line.delivery_status in ('received','in_transit','delivered','failed','returned'):
            ts.append(('picked',  line.create_date))
        if line.delivery_status in ('in_transit','delivered'):
            ts.append(('out',     line.write_date))
        if line.delivery_status == 'delivered':
            ts.append(('delivered', line.delivery_date_actual or line.write_date))
        if line.delivery_status == 'failed':
            ts.append(('failed',    line.write_date))
        out['timeline'] = [{
            'code': c,
            'label': status_label(c),
            'when': (when or datetime.now()).isoformat(),
        } for (c, when) in ts]
    return out


def _get_active_line(order_id, driver):
    Line = request.env['delivery.trip.line'].sudo()
    line = Line.search([
        ('sale_order_id', '=', order_id),
        ('driver_id', '=', driver.id),
    ], limit=1, order='id desc')
    return line


class DriverOrdersAPI(http.Controller):

    @http.route('/api/driver/v1/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_orders(self, **kw):
        driver = current_driver()
        p = get_payload()
        status = (p.get('status') or '').strip()
        search = (p.get('search') or '').strip()
        try:
            page = max(1, int(p.get('page') or 1))
            per_page = min(50, max(5, int(p.get('per_page') or 20)))
        except (TypeError, ValueError):
            page, per_page = 1, 20

        Line = request.env['delivery.trip.line'].sudo()
        domain = [('driver_id', '=', driver.id)]
        if status == 'active':
            domain += [('delivery_status', 'in', ('pending', 'received', 'in_transit'))]
        elif status == 'done':
            domain += [('delivery_status', '=', 'delivered')]
        elif status == 'failed':
            domain += [('delivery_status', '=', 'failed')]
        elif status == 'returned':
            domain += [('delivery_status', '=', 'returned')]
        if search:
            domain += ['|', ('sale_order_id.name', 'ilike', search),
                            ('sale_order_id.partner_id.name', 'ilike', search)]
        total = Line.search_count(domain)
        offset = (page - 1) * per_page
        rows = Line.search(domain, order='sequence asc, id desc',
                            limit=per_page, offset=offset)
        items = [it for it in (_serialize_line(l) for l in rows) if it]
        return ok(items, meta={
            'page': page, 'per_page': per_page,
            'total': total, 'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/driver/v1/orders/<int:order_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_detail(self, order_id, **kw):
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned to you', 404)
        return ok({'order': _serialize_line(line, detail=True)})

    @http.route('/api/driver/v1/orders/<int:order_id>/pickup', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def pickup(self, order_id, **kw):
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        line.sudo().write({'delivery_status': 'received'})
        line.sale_order_id.message_post(body=f'📦 Picked up by {driver.name}')
        return ok({'status': 'picked'})

    @http.route('/api/driver/v1/orders/<int:order_id>/decline', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def decline(self, order_id, **kw):
        p = get_payload()
        reason = (p.get('reason') or 'Driver declined').strip()
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        line.sudo().write({'driver_id': False, 'notes': (line.notes or '') +
                            f'\nDeclined by {driver.name}: {reason}'})
        line.sale_order_id.message_post(body=f'🚫 Declined by {driver.name}: {reason}')
        return ok({'declined': True})

    @http.route('/api/driver/v1/orders/<int:order_id>/start', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def start(self, order_id, **kw):
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        line.sudo().write({'delivery_status': 'in_transit'})
        line.sale_order_id.message_post(body=f'🚚 Out for delivery — {driver.name}')
        return ok({'status': 'out'})

    @http.route('/api/driver/v1/orders/<int:order_id>/confirm', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def confirm(self, order_id, **kw):
        p = get_payload()
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        vals = {
            'delivery_status': 'delivered',
            'delivery_date_actual': fields.Datetime.now(),
            'notes': (p.get('notes') or '').strip(),
        }
        if p.get('proof_image_base64'):
            try:
                raw = base64.b64decode(p['proof_image_base64'].split(',', 1)[-1])
                vals['proof_image'] = base64.b64encode(raw)
                vals['proof_image_filename'] = f'proof_{order_id}.jpg'
            except (binascii.Error, ValueError):
                pass
        if p.get('signature_base64'):
            try:
                raw = base64.b64decode(p['signature_base64'].split(',', 1)[-1])
                vals['proof_signature'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        line.sudo().write(vals)
        line.sale_order_id.message_post(
            body=f'✅ Delivered by {driver.name}. Cash: {p.get("cash_collected", 0)} KD')
        return ok({'status': 'delivered'})

    @http.route('/api/driver/v1/orders/<int:order_id>/fail', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def fail_(self, order_id, **kw):
        p = get_payload()
        reason = (p.get('reason') or 'Unknown').strip()
        details = (p.get('details') or '').strip()
        return_to_uellow = bool(p.get('return_to_uellow'))
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        line.sudo().write({
            'delivery_status': 'failed',
            'failure_reason': reason,
            'failure_returned': return_to_uellow,
            'failure_returned_date': fields.Datetime.now() if return_to_uellow else False,
            'notes': details,
        })
        line.sale_order_id.message_post(
            body=f'❌ Delivery failed ({reason}) by {driver.name}. '
                  f'{"Returning to warehouse." if return_to_uellow else ""}')
        return ok({'status': 'failed'})

    @http.route('/api/driver/v1/orders/<int:order_id>/return', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def return_(self, order_id, **kw):
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        line.sudo().write({
            'delivery_status': 'returned',
            'failure_returned': True,
            'failure_returned_date': fields.Datetime.now(),
        })
        line.sale_order_id.message_post(body=f'↩ Returned to Uellow by {driver.name}')
        return ok({'status': 'returned'})
