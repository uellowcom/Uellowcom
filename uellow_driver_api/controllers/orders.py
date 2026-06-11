# -*- coding: utf-8 -*-
"""Driver orders — /api/driver/v1/orders*

list / detail / pickup / decline / start / confirm / fail / return
"""
import base64
import binascii
import re
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
    bilingual, fmt_price, short_addr, order_payment_method,
    order_status_code, status_label,
)


def _notify_customer(order, event_code, title_en, title_ar, body_en, body_ar):
    """v2.2.32 — best-effort customer push when the driver moves the order
    (out-for-delivery / delivered). Previously the driver actions only wrote
    an internal chatter note, so the CUSTOMER was never notified. Guarded —
    never breaks the driver action if the engine is missing."""
    try:
        if not order or not order.partner_id:
            return
        Eng = request.env.get('mobile.customer.notification')
        if Eng is None:
            return
        Eng.sudo().push_event(order.partner_id, event_code,
                              title_en, title_ar, body_en, body_ar,
                              {'type': 'order', 'id': order.id})
    except Exception:
        pass


def _refresh_broadcast(driver):
    """Keep driver.is_broadcasting True only while at least one delivery is
    still out_for_delivery; turn it off when the driver finished his last
    active stop (stops the live pin on customers' maps)."""
    try:
        if not driver or 'is_broadcasting' not in driver._fields:
            return
        Line = request.env['delivery.trip.line'].sudo()
        active = Line.search_count([
            ('driver_id', '=', driver.id),
            ('delivery_status', '=', 'out_for_delivery'),
        ])
        driver.sudo().write({'is_broadcasting': bool(active)})
    except Exception:
        pass


def _order_geo(line):
    """(lat, lng) for a trip line's delivery address, or (None, None)."""
    o = line.sale_order_id
    if not o:
        return (None, None)
    if getattr(o, 'delivery_lat', 0) and getattr(o, 'delivery_lng', 0):
        return (o.delivery_lat, o.delivery_lng)
    p = o.partner_shipping_id or o.partner_id
    lat = getattr(p, 'partner_latitude', 0)
    lng = getattr(p, 'partner_longitude', 0)
    return (lat or None, lng or None)


def _sort_by_proximity(lines, from_lat, from_lng):
    """Sort trip lines by great-circle distance from the driver. Stops with
    no coordinates fall to the end (preserving their sequence order)."""
    try:
        from odoo.addons.uellow_mobile_manager.models.tracking_extras import haversine_km
    except Exception:
        return lines
    def key(line):
        lat, lng = _order_geo(line)
        d = haversine_km(from_lat, from_lng, lat, lng) if (lat and lng) else None
        return (d is None, d if d is not None else 0.0, line.sequence or 0, line.id)
    return lines.sorted(key=key)


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
        # combine the customer order note + any line note, cleaned.
        out['notes'] = _clean_notes('\n'.join(
            n for n in [getattr(o, 'note', '') or '', line.notes or ''] if n))
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
        if line.delivery_status in ('accepted','out_for_delivery','delivered','failed','failed_returned','returned'):
            ts.append(('accepted', line.create_date))
        if line.delivery_status in ('out_for_delivery','delivered'):
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


def _clean_notes(raw):
    """v2.2.33 — driver-facing notes must be plain human text. Strip HTML
    tags and drop internal/technical lines (e.g. the 'Payment: …' marker the
    checkout appends) so the driver doesn't see raw code."""
    if not raw:
        return ''
    txt = re.sub(r'<[^>]+>', ' ', str(raw))          # strip HTML tags
    txt = txt.replace('&nbsp;', ' ').replace('&amp;', '&')
    lines = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if low.startswith('payment:') or low.startswith('الدفع:'):
            continue
        lines.append(s)
    return '\n'.join(lines).strip()


def _set_status(line, status, line_vals=None):
    """v2.2.33 — the SOURCE OF TRUTH is sale_order.delivery_status. The trip
    line's delivery_status is a stored-related WITHOUT an inverse, so writing
    the line does NOT propagate to the order (and the customer reads the
    order). We therefore write the ORDER and let the line follow; line-only
    fields (proof, notes, failure_reason…) are written on the line. We pass
    skip_push so the model's own stage-push doesn't double up with the
    explicit _notify_customer calls below."""
    line.sale_order_id.sudo().with_context(skip_push=True).write(
        {'delivery_status': status})
    if line_vals:
        line.sudo().write(line_vals)


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
        # v2.2.32 — the carrier-portal sets the order/line status to
        # 'assigned' / 'arrived_sorting' / 'out_for_delivery', but this list
        # was filtering on a stale vocabulary ('pending','received',
        # 'in_transit'), so freshly-ASSIGNED orders never showed even though
        # the driver got the push. 'active' is now EVERYTHING not finished.
        _TERMINAL = ('delivered', 'failed', 'failed_returned', 'returned', 'cancelled')
        if status == 'active':
            domain += [('delivery_status', 'not in', _TERMINAL)]
        elif status == 'done':
            domain += [('delivery_status', '=', 'delivered')]
        elif status == 'failed':
            domain += [('delivery_status', '=', 'failed')]
        elif status == 'returned':
            domain += [('delivery_status', 'in', ('failed_returned', 'returned'))]
        if search:
            domain += ['|', ('sale_order_id.name', 'ilike', search),
                            ('sale_order_id.partner_id.name', 'ilike', search)]
        total = Line.search_count(domain)
        # v2.2.33 — nearest-first ordering. When the driver has a live GPS
        # fix, sort the ACTIVE list by real distance to each stop (this
        # naturally clusters the same country → governorate → city → street,
        # closest first). Falls back to the manual sequence when there's no
        # GPS or for the done/failed tabs.
        if status in ('', 'active') and driver.current_lat and driver.current_lng:
            rows = Line.search(domain, order='sequence asc, id desc', limit=200)
            rows = _sort_by_proximity(rows, driver.current_lat, driver.current_lng)
            offset = (page - 1) * per_page
            rows = rows[offset:offset + per_page]
        else:
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
        # legacy endpoint — kept for old app builds; behaves like Accept.
        _set_status(line, 'accepted')
        line.sale_order_id.message_post(body=f'📦 Picked up by {driver.name}')
        return ok({'status': 'accepted'})

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
        line.sale_order_id.sudo().with_context(skip_push=True).write(
            {'delivery_driver_id': False, 'delivery_status': 'arrived_sorting'})
        line.sudo().write({'driver_id': False, 'notes': (line.notes or '') +
                            f'\nDeclined by {driver.name}: {reason}'})
        line.sale_order_id.message_post(body=f'🚫 Declined by {driver.name}: {reason}')
        return ok({'declined': True})

    @http.route('/api/driver/v1/orders/<int:order_id>/accept', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def accept(self, order_id, **kw):
        """v2.2.33 — driver ACCEPTS a new assignment. The order becomes
        'accepted' (with the courier); the customer is told the order is now
        with the courier, but live tracking does NOT start until the driver
        presses "Start delivery"."""
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned to you', 404)
        _set_status(line, 'accepted')
        line.sale_order_id.message_post(body=f'✅ Accepted by {driver.name}')
        _notify_customer(line.sale_order_id, 'order_with_courier',
            'With the courier 📦', 'طلبك مع المندوب 📦',
            'Your order %s is now with the courier and will be on its way soon.' % line.sale_order_id.name,
            'طلبك %s أصبح مع المندوب وسيكون في الطريق إليك قريباً.' % line.sale_order_id.name)
        return ok({'status': 'accepted'})

    @http.route('/api/driver/v1/orders/<int:order_id>/reject', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def reject(self, order_id, **kw):
        """v2.2.33 — driver REJECTS a new assignment. The order goes back to
        the sorting center (arrived_sorting) and the driver is unassigned, so
        the carrier can re-assign it to someone else."""
        p = get_payload()
        reason = (p.get('reason') or 'Driver rejected').strip()
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned to you', 404)
        order = line.sale_order_id
        order.sudo().with_context(skip_push=True).write({
            'delivery_driver_id': False,
            'delivery_status': 'arrived_sorting'})
        line.sudo().write({
            'driver_id': False,
            'notes': (line.notes or '') + f'\nRejected by {driver.name}: {reason}',
        })
        order.message_post(body=f'🚫 Rejected by {driver.name}: {reason} '
                                f'— back to sorting center for re-assignment.')
        return ok({'rejected': True})

    @http.route('/api/driver/v1/orders/<int:order_id>/start', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def start(self, order_id, **kw):
        driver = current_driver()
        line = _get_active_line(order_id, driver)
        if not line:
            return fail('NOT_FOUND', 'Order not assigned', 404)
        # v2.2.32 — "Start delivery" must set 'out_for_delivery' (the status
        # the CUSTOMER live-tracking gate keys on) — it used to set the
        # phantom 'in_transit', so tracking_stage() never reached in_transit
        # and the customer never saw the driver. Also flip the driver to
        # broadcasting so location heartbeats are shown live.
        _set_status(line, 'out_for_delivery')
        try:
            if 'is_broadcasting' in driver._fields:
                driver.sudo().write({'is_broadcasting': True})
        except Exception:
            pass
        line.sale_order_id.message_post(body=f'🚚 Out for delivery — {driver.name}')
        _notify_customer(line.sale_order_id, 'order_out_for_delivery',
            'On the way 🚚', 'طلبك في الطريق إليك 🚚',
            'Your order %s is out for delivery now — track your courier live.' % line.sale_order_id.name,
            'طلبك %s في الطريق إليك الآن — تابع مندوبك مباشرة على الخريطة.' % line.sale_order_id.name)
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
        now = fields.Datetime.now()
        line_vals = {
            'delivery_date_actual': now,
            'notes': (p.get('notes') or '').strip(),
        }
        if p.get('proof_image_base64'):
            try:
                raw = base64.b64decode(p['proof_image_base64'].split(',', 1)[-1])
                line_vals['proof_image'] = base64.b64encode(raw)
                line_vals['proof_image_filename'] = f'proof_{order_id}.jpg'
            except (binascii.Error, ValueError):
                pass
        if p.get('signature_base64'):
            try:
                raw = base64.b64decode(p['signature_base64'].split(',', 1)[-1])
                line_vals['proof_signature'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        _set_status(line, 'delivered', line_vals)
        # order-level delivery time + cash collection flag for COD
        order = line.sale_order_id
        order_vals = {'delivery_date_actual': now}
        if order.payment_method_type == 'cash':
            order_vals['cash_collection_status'] = 'collected'
        order.sudo().with_context(skip_push=True).write(order_vals)
        line.sale_order_id.message_post(
            body=f'✅ Delivered by {driver.name}. Cash: {p.get("cash_collected", 0)} KD')
        _notify_customer(line.sale_order_id, 'order_delivered',
            'Delivered ✅', 'تم تسليم طلبك ✅',
            'Your order %s has been delivered. Thank you!' % line.sale_order_id.name,
            'تم تسليم طلبك %s بنجاح. شكراً لك!' % line.sale_order_id.name)
        _refresh_broadcast(driver)
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
        _set_status(line, 'failed_returned' if return_to_uellow else 'failed', {
            'failure_reason': reason,
            'failure_returned': return_to_uellow,
            'failure_returned_date': fields.Datetime.now() if return_to_uellow else False,
            'notes': details,
        })
        line.sale_order_id.message_post(
            body=f'❌ Delivery failed ({reason}) by {driver.name}. '
                  f'{"Returning to warehouse." if return_to_uellow else ""}')
        _refresh_broadcast(driver)
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
        _set_status(line, 'failed_returned', {
            'failure_returned': True,
            'failure_returned_date': fields.Datetime.now(),
        })
        line.sale_order_id.message_post(body=f'↩ Returned to Uellow by {driver.name}')
        _refresh_broadcast(driver)
        return ok({'status': 'returned'})

    @http.route('/api/driver/v1/location', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_location(self, **kw):
        """v2.2.32 — driver GPS heartbeat. The app was sending its location
        nowhere (no endpoint existed), so the customer's live map never had a
        driver pin. This stores current_lat/lng + flips is_broadcasting on
        while the driver has an out-for-delivery stop. Call every ~15-20s
        while on an active delivery."""
        driver = current_driver()
        p = get_payload()
        try:
            lat = float(p.get('lat'))
            lng = float(p.get('lng'))
        except (TypeError, ValueError):
            return fail('BAD_INPUT', 'lat and lng are required')
        vals = {
            'current_lat': lat, 'current_lng': lng,
            'location_updated_at': fields.Datetime.now(),
        }
        broadcasting = True
        if 'is_broadcasting' in driver._fields:
            active = request.env['delivery.trip.line'].sudo().search_count([
                ('driver_id', '=', driver.id),
                ('delivery_status', '=', 'out_for_delivery'),
            ])
            broadcasting = bool(active)
            vals['is_broadcasting'] = broadcasting
        driver.sudo().write(vals)
        return ok({'saved': True, 'broadcasting': broadcasting})
