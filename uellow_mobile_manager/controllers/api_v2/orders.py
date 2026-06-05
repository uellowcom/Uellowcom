"""
Orders & checkout — /api/mobile/v2/orders/*

list                GET   /                          → user's orders
detail              GET   /<id>                       → one order
shipping_methods    GET   /shipping-methods           → available methods for cart
payment_methods     GET   /payment-methods            → available providers
checkout_summary    GET   /checkout/summary           → totals + addresses + methods
checkout_confirm    POST  /checkout/confirm           → place order, returns payment URL or order
"""
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    img_url, base_url, fmt_price, bilingual, get_lang, get_website, app_setting,
)
from .cart import (_get_or_create_order, serialize_cart,
                   effective_shipping_price, carrier_is_express,
                   selected_line_ids, subset_view, split_cart_for_checkout)


def _guest_gate(p_or_kw):
    """Guest checkout gate: returns (partner, error_response). Guests pass
    only when the per-website setting is ON and the client explicitly sent
    guest=1 (the app shows the lose-perks warning first)."""
    partner = current_partner()
    if partner:
        return partner, None
    guest_flag = str(p_or_kw.get('guest') or '') in ('1', 'true', 'True')
    enabled = bool(getattr(app_setting(), 'guest_checkout_enabled', False))
    if guest_flag and enabled:
        return None, None
    return None, fail('AUTH_REQUIRED', 'You must be logged in.', 401)


def _apply_delivery_preserving_rewards(order, carrier, price):
    """Add the delivery line via set_delivery_line but keep coupon reward
    lines (Odoo's set_delivery_line can drop them)."""
    saved = [(r.product_id.id, r.product_uom_qty, r.price_unit, r.name)
             for r in order.order_line.filtered('is_reward_line')]
    try:
        order.set_delivery_line(carrier, price)
    except Exception:
        pass
    try:
        if hasattr(order, '_update_programs_and_rewards'):
            order._update_programs_and_rewards()
    except Exception:
        pass
    if (not order.order_line.filtered('is_reward_line')) and saved:
        for prod_id, qty, price_unit, name in saved:
            try:
                order.env['sale.order.line'].sudo().create({
                    'order_id': order.id, 'product_id': prod_id,
                    'product_uom_qty': qty, 'price_unit': price_unit,
                    'name': name, 'is_reward_line': True,
                })
            except Exception:
                pass


def serialize_order(order, detail=False):
    cur = order.currency_id or request.env.company.currency_id
    u_status = _uellow_status(order)
    base = {
        'id': order.id,
        'name': order.name,
        'state': order.state,
        'state_label': _state_label(order.state),
        # Unified bilingual status — combines sale state + delivery_status
        # + return_status into one app-friendly enum used by the orders
        # block, filter chips, timeline and order detail.
        'uellow_status': u_status['code'],
        'uellow_status_label': u_status['label'],
        'date': order.date_order and order.date_order.isoformat() or None,
        'total': fmt_price(order.amount_total, cur),
        'line_count': len(order.order_line.filtered(lambda l: not l.display_type and not l.is_reward_line)),
        # v2.1.42 — customer cancellation: allowed while draft/confirmed.
        # Paid orders turn into an admin-approval request instead.
        'can_cancel': (u_status['code'] in ('draft', 'confirmed')
                       and not getattr(order, 'cancel_request', False)),
        'cancel_requested': bool(getattr(order, 'cancel_request', False)),
        'is_paid': _order_is_paid(order),
    }
    if not detail:
        return base
    lines = []
    for l in order.order_line.filtered(lambda l: not l.display_type):
        product = l.product_id
        lines.append({
            'id': l.id,
            'product_id': product.product_tmpl_id.id,
            'variant_id': product.id,
            'name': bilingual(product.product_tmpl_id, 'name'),
            'image': img_url('product.product', product.id, 'image_256',
                             unique=product.write_date),
            'qty': l.product_uom_qty,
            'unit_price': fmt_price(l.price_unit, cur),
            'subtotal':   fmt_price(l.price_subtotal, cur),
            'total':      fmt_price(l.price_total, cur),
            'sku':        product.default_code or '',
            'attributes': [],
            'is_reward':  bool(l.is_reward_line),
        })
    delivery = order.partner_shipping_id
    invoice = order.partner_invoice_id
    return {
        **base,
        'lines': lines,
        'subtotal': fmt_price(order.amount_untaxed, cur),
        'tax':      fmt_price(order.amount_tax, cur),
        'shipping': fmt_price(order.amount_delivery or 0, cur),
        'delivery_address': {
            'id': delivery.id,
            'name': delivery.name,
            'phone': delivery.phone or delivery.mobile or '',
            'street': delivery.street or '',
            'street2': delivery.street2 or '',
            'city': delivery.city or '',
            'country': delivery.country_id.name if delivery.country_id else '',
            'zip': delivery.zip or '',
        } if delivery else None,
        'invoice_address': {
            'id': invoice.id,
            'name': invoice.name,
            'phone': invoice.phone or '',
        } if invoice else None,
        'payment': {
            'state': order.invoice_status,
            'method': order.payment_term_id.name if order.payment_term_id else '',
        },
        'tracking_number': getattr(order, 'tracking_number', '') or '',
        'carrier': order.carrier_id.name if order.carrier_id else '',
        # Driver / tracking — live from delivery_carrier_portal when set
        'delivery_tracking': _delivery_tracking(order),
        'timeline': _order_timeline(order),
    }


def _state_label(state):
    return {
        'draft':    {'en': 'Draft',     'ar': 'مسودة'},
        'sent':     {'en': 'Sent',      'ar': 'مرسل'},
        'sale':     {'en': 'Confirmed', 'ar': 'مؤكد'},
        'done':     {'en': 'Done',      'ar': 'مكتمل'},
        'cancel':   {'en': 'Cancelled', 'ar': 'ملغي'},
    }.get(state, {'en': state, 'ar': state})


# ─── Unified order status ────────────────────────────────────────────
#
# The app speaks one vocabulary; here we collapse Odoo's parallel state
# machines (sale.state + delivery_carrier_portal.delivery_status +
# return_status) into a single ordered enum:
#
#   draft → confirmed → preparing → shipping → delivered
#                                  ↘
#                                   cancelled / returned
#
# Each entry returns {code, label{en,ar}, badge_color, step_index} so
# the app can render chips, timelines and filter buttons consistently.
def _carrier_now_availability(c):
    """v2.1.55 — (available_now, note{en,ar}|None) from the weekly
    schedule windows + the zone cutoff. Mirrors delivery-eta."""
    from datetime import datetime
    import pytz
    try:
        tz = pytz.timezone(request.env.user.tz or 'Asia/Kuwait')
        now = datetime.now(tz)
        is_now = True
        opens_note = None
        avail = getattr(c, 'availability_ids', None)
        if avail:
            hour = now.hour + now.minute / 60.0
            wins = [a for a in avail if int(a.weekday) == now.weekday()]
            is_now = any(a.hour_from <= hour < a.hour_to for a in wins)
        if is_now:
            cutoff = ''
            try:
                z = c.uellow_zone_ids[:1] if getattr(
                    c, 'uellow_zone_ids', False) else None
                cutoff = (z.cutoff_time or '') if z else ''
            except Exception:
                pass
            if cutoff:
                try:
                    parts = (cutoff.split(':') + ['0'])[:2] \
                        if ':' in cutoff else [cutoff, '0']
                    if (now.hour * 60 + now.minute) >= \
                            (int(parts[0]) * 60 + int(parts[1])):
                        is_now = False
                        opens_note = {
                            'en': 'Unavailable now — order cutoff %s '
                                  'passed, delivers tomorrow' % cutoff,
                            'ar': 'غير متاح الآن — انتهى وقت الطلب '
                                  '(%s)، التوصيل غداً' % cutoff,
                        }
                except Exception:
                    pass
        if not is_now and opens_note is None:
            opens_note = {'en': 'Unavailable right now',
                          'ar': 'غير متاح حالياً'}
        return is_now, (None if is_now else opens_note)
    except Exception:
        return True, None


def _order_is_paid(order):
    """v2.1.42 — captured/authorized online payment OR a paid invoice."""
    try:
        if any(t.state in ('done', 'authorized')
               for t in order.transaction_ids):
            return True
        if any(inv.payment_state in ('paid', 'in_payment')
               for inv in order.invoice_ids):
            return True
    except Exception:
        pass
    return False


_UELLOW_STATUS_DICT = {
    'draft':     {'en': 'Draft',      'ar': 'مسودة',     'color': '#9C8A5E', 'idx': 0},
    'confirmed': {'en': 'Confirmed',  'ar': 'مؤكد',      'color': '#0EA5E9', 'idx': 1},
    'preparing': {'en': 'Preparing',  'ar': 'قيد التجهيز', 'color': '#8B5CF6', 'idx': 2},
    'shipping':  {'en': 'Shipping',   'ar': 'قيد الشحن',  'color': '#F59E0B', 'idx': 3},
    'delivered': {'en': 'Delivered',  'ar': 'تم التسليم',  'color': '#10B981', 'idx': 4},
    'cancelled': {'en': 'Cancelled',  'ar': 'ملغي',      'color': '#9CA3AF', 'idx': 5},
    'returned':  {'en': 'Returned',   'ar': 'مرتجع',     'color': '#EF4444', 'idx': 6},
}


def _uellow_status(order):
    """Map an Odoo sale.order to the unified Uellow status enum."""
    state = order.state
    ds = getattr(order, 'delivery_status', None)
    rs = getattr(order, 'return_status', None)
    if state == 'cancel':
        code = 'cancelled'
    elif rs in ('returned_received',):
        code = 'returned'
    elif ds == 'delivered':
        code = 'delivered'
    elif ds in ('assigned', 'out_for_delivery'):
        code = 'shipping'
    elif ds in ('arrived_sorting',) or state == 'sale':
        code = 'preparing' if ds == 'arrived_sorting' else 'confirmed'
    elif state in ('draft', 'sent'):
        code = 'draft'
    else:
        code = 'draft'
    meta = _UELLOW_STATUS_DICT[code]
    return {
        'code': code,
        'label': {'en': meta['en'], 'ar': meta['ar']},
        'color': meta['color'],
        'step': meta['idx'],
    }


def _delivery_tracking(order):
    """Rich tracking block — locations of warehouse, carrier center,
    customer, and (when broadcasting) the live driver van. Returns the
    stage so the app can pick the right map layer.

    Returns at minimum the warehouse pin once the order is confirmed;
    None only for draft/cancelled orders where a map makes no sense."""
    if order.state in ('draft', 'sent', 'cancel'):
        return None
    try:
        stage = order.tracking_stage() if hasattr(order, 'tracking_stage') else 'placed'
    except Exception:
        stage = 'placed'
    # Warehouse pin — from mobile.app.setting (one per website).
    setting = app_setting()
    warehouse = None
    if setting and (setting.warehouse_lat or setting.warehouse_lng):
        warehouse = {
            'lat': setting.warehouse_lat,
            'lng': setting.warehouse_lng,
            'name': {'en': setting.warehouse_name_en or 'Uellow Warehouse',
                     'ar': setting.warehouse_name_ar or 'مخزن يلو'},
            'address': setting.warehouse_address or '',
        }
    # Carrier pin
    carrier = None
    if order.delivery_carrier_company_id and (
            order.delivery_carrier_company_id.center_lat
            or order.delivery_carrier_company_id.center_lng):
        cc = order.delivery_carrier_company_id
        carrier = {
            'id': cc.id,
            'lat': cc.center_lat, 'lng': cc.center_lng,
            'name': cc.name or '',
            'logo': img_url('delivery.carrier.company', cc.id, 'logo',
                            unique=cc.write_date) if cc.logo else None,
            'address': cc.center_address or '',
            'phone': cc.phone or '',
        }
    # Customer pin (delivery address)
    customer = None
    if getattr(order, 'delivery_lat', 0) or getattr(order, 'delivery_lng', 0):
        customer = {
            'lat': order.delivery_lat,
            'lng': order.delivery_lng,
            'address': order.delivery_address_text or (
                order.partner_shipping_id.contact_address if order.partner_shipping_id else ''),
        }
    elif order.partner_shipping_id and order.partner_shipping_id.partner_latitude:
        # Fallback to res.partner geocoded lat/lng if order-level wasn't set.
        customer = {
            'lat': order.partner_shipping_id.partner_latitude,
            'lng': order.partner_shipping_id.partner_longitude,
            'address': order.partner_shipping_id.contact_address or '',
        }
    # Driver pin (only while broadcasting / out for delivery)
    driver = None
    drv = order.delivery_driver_id
    if drv:
        is_live = bool(drv.is_broadcasting and drv.current_lat and drv.current_lng
                        and stage in ('in_transit', 'arriving'))
        driver = {
            'id': drv.id,
            'name': drv.name,
            'phone': drv.phone or '',
            'photo': img_url('delivery.driver', drv.id, 'photo',
                              unique=drv.write_date) if getattr(drv, 'photo', False) else None,
            'lat': drv.current_lat if is_live else None,
            'lng': drv.current_lng if is_live else None,
            'is_live': is_live,
            'updated_at': drv.location_updated_at.isoformat() if drv.location_updated_at else None,
        }
    # Distance + ETA
    distance_km = None
    if driver and driver.get('is_live') and customer:
        try:
            from odoo.addons.uellow_mobile_manager.models.tracking_extras import haversine_km
            distance_km = haversine_km(driver['lat'], driver['lng'],
                                        customer['lat'], customer['lng'])
        except Exception:
            distance_km = None
    return {
        'stage': stage,
        'stage_label': _stage_label(stage),
        'status': getattr(order, 'delivery_status', None),
        'warehouse': warehouse,
        'carrier': carrier,
        'customer': customer,
        'driver': driver,
        'distance_km': round(distance_km, 2) if distance_km is not None else None,
        'eta_text': _eta_text(order),
        # Back-compat aliases (older app builds)
        'driver_name':  drv.name if drv else '',
        'driver_phone': (drv.phone or '') if drv else '',
        'driver_photo': (img_url('delivery.driver', drv.id, 'photo',
                                  unique=drv.write_date)
                          if drv and getattr(drv, 'photo', False) else None),
        'lat': driver['lat'] if driver else None,
        'lng': driver['lng'] if driver else None,
        'address_text': customer['address'] if customer else '',
    }


def _stage_label(stage):
    return {
        'placed':       {'en': 'Order placed',           'ar': 'تم استلام الطلب'},
        'at_warehouse': {'en': 'Preparing at warehouse', 'ar': 'قيد التحضير بالمخزن'},
        # v2.1.72 — "assigned to a courier" wording (مندوب), not "driver".
        'at_carrier':   {'en': 'Assigned to a courier',  'ar': 'تم إسناد طلبك إلى أحد المناديب'},
        'in_transit':   {'en': 'Courier on the way',     'ar': 'المندوب في الطريق إليك'},
        'arriving':     {'en': 'Arriving — be ready',    'ar': 'يقترب — كن جاهزاً'},
        'delivered':    {'en': 'Delivered',              'ar': 'تم التسليم'},
        'cancelled':    {'en': 'Cancelled',              'ar': 'ملغي'},
        'returned':     {'en': 'Returned',               'ar': 'مرتجع'},
    }.get(stage, {'en': stage, 'ar': stage})


def _eta_text(order):
    """Best-effort delivery ETA copy — bilingual."""
    ds = getattr(order, 'delivery_status', None)
    if ds == 'out_for_delivery':
        return {'en': 'Out for delivery · arriving soon',
                'ar': 'في الطريق إليك · يصل قريباً'}
    if ds == 'assigned':
        return {'en': 'Assigned to a courier · preparing pickup',
                'ar': 'تم إسناد طلبك إلى أحد المناديب · جارٍ التحضير للاستلام'}
    if ds == 'delivered':
        return {'en': 'Delivered', 'ar': 'تم التسليم'}
    if ds == 'arrived_sorting':
        return {'en': 'At sorting center', 'ar': 'في مركز الفرز'}
    return {'en': 'Order placed', 'ar': 'تم استلام الطلب'}


# v2.1.72 — per-step bilingual descriptions for the tracking timeline.
_TIMELINE_DESC = {
    'draft':     {'en': 'Your order was received',
                  'ar': 'تم استلام طلبك'},
    'confirmed': {'en': 'Order confirmed and being processed',
                  'ar': 'تم تأكيد الطلب وجارٍ معالجته'},
    'preparing': {'en': 'Your items are being packed',
                  'ar': 'جارٍ تجهيز وتغليف منتجاتك'},
    'shipping':  {'en': 'Handed to a courier, on the way to you',
                  'ar': 'تم تسليمه لأحد المناديب في طريقه إليك'},
    'delivered': {'en': 'Delivered — enjoy!',
                  'ar': 'تم التسليم — نتمنى لك تجربة سعيدة'},
}


def _fmt_dt(dt):
    """ISO + a friendly 'YYYY-MM-DD HH:MM' for the timeline."""
    if not dt:
        return None, ''
    try:
        return dt.isoformat(), dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return None, ''


def _step_timestamp(order, code):
    """Best-effort real timestamp for each step, from the order's own
    dates (no extra audit model needed)."""
    if code == 'draft':
        return order.create_date
    if code == 'confirmed':
        return order.date_order or order.create_date
    if code == 'delivered':
        return getattr(order, 'delivery_date_actual', None) or order.write_date
    # preparing / shipping — we don't keep a dedicated stamp; fall back to
    # the order write_date only for the CURRENT step so past steps still
    # show their natural time and future ones stay blank.
    return None


def _order_timeline(order):
    """Per-step timeline used by the tracking screen — every Uellow
    status with done/current/upcoming markers, a real date+time, and a
    short human description."""
    current = _uellow_status(order)['code']
    cur_idx = _UELLOW_STATUS_DICT[current]['idx']
    out = []
    for code in ('draft', 'confirmed', 'preparing', 'shipping', 'delivered'):
        meta = _UELLOW_STATUS_DICT[code]
        state = 'done' if meta['idx'] < cur_idx else (
            'current' if meta['idx'] == cur_idx else 'upcoming')
        if current in ('cancelled', 'returned'):
            state = 'done' if meta['idx'] <= 1 else 'upcoming'
        # timestamp: real stamp where we have one; for the CURRENT step
        # with no dedicated stamp use write_date so it isn't blank.
        ts = _step_timestamp(order, code)
        if ts is None and state == 'current':
            ts = order.write_date
        iso, human = _fmt_dt(ts) if (state != 'upcoming' and ts) else (None, '')
        out.append({
            'code': code,
            'label': {'en': meta['en'], 'ar': meta['ar']},
            'description': _TIMELINE_DESC.get(code, {'en': '', 'ar': ''}),
            'state': state,
            'date': iso,
            'date_text': human,
        })
    return out


class MobileOrdersAPI(http.Controller):

    @http.route('/api/mobile/v2/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_orders(self, **kw):
        from ._common import paginate
        p = get_payload()
        partner = current_partner()
        # Map app-side filter values onto sale.order states.
        # delivery_carrier_portal flow uses delivery_status separately for
        # confirmed/shipping/delivered — read that when available.
        # Accept either the legacy ?state=... filter OR the new unified
        # ?status=draft|confirmed|preparing|shipping|delivered|cancelled|returned.
        state = (p.get('status') or p.get('state') or '').strip().lower()
        domain = [
            ('partner_id', '=', partner.id),
            ('state', 'in', ['draft', 'sent', 'sale', 'done', 'cancel']),
        ]
        has_ds = 'delivery_status' in request.env['sale.order']._fields
        has_rs = 'return_status' in request.env['sale.order']._fields
        if state == 'draft':
            domain += [('state', 'in', ['draft', 'sent'])]
        elif state == 'confirmed':
            if has_ds:
                domain += [('state', '=', 'sale'),
                           ('delivery_status', 'in', ['pending', 'confirmed', False])]
            else:
                domain += [('state', '=', 'sale')]
        elif state == 'preparing' and has_ds:
            domain += [('delivery_status', '=', 'arrived_sorting')]
        elif state == 'shipping' and has_ds:
            domain += [('delivery_status', 'in', ['assigned', 'out_for_delivery'])]
        elif state == 'delivered':
            if has_ds:
                domain += [('delivery_status', '=', 'delivered')]
            else:
                domain += [('state', '=', 'done')]
        elif state == 'cancelled' or state == 'cancel':
            domain = [('partner_id', '=', partner.id), ('state', '=', 'cancel')]
        elif state == 'returned' and has_rs:
            domain += [('return_status', '=', 'returned_received')]
        elif state == 'sale':
            domain += [('state', '=', 'sale')]
        orders = request.env['sale.order'].sudo().search(domain, order='date_order desc')
        items, meta = paginate(
            orders, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda o: serialize_order(o, detail=False),
        )
        return ok(items, meta)

    @http.route('/api/mobile/v2/orders/<int:order_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_detail(self, order_id, **kw):
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)
        return ok({'order': serialize_order(order, detail=True)})

    @http.route('/api/mobile/v2/orders/<int:order_id>/cancel', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_cancel(self, order_id, **kw):
        """v2.1.42 — customer cancellation.
        draft / confirmed + UNPAID  → cancel immediately.
        draft / confirmed + PAID    → raise an admin-approval request.
        anything later              → not allowed."""
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)
        if getattr(order, 'cancel_request', False):
            return ok({'result': 'requested'})
        code = _uellow_status(order)['code']
        if code not in ('draft', 'confirmed'):
            return fail('NOT_ALLOWED',
                        'Order can no longer be cancelled', 400)
        p = get_payload()
        reason = (p.get('reason') or '').strip()[:300]
        paid = _order_is_paid(order)
        if paid and code != 'draft':
            # paid → needs admin approval (refund handled by the admin)
            order.write({
                'cancel_request': True,
                'cancel_request_date': datetime.now(),
                'cancel_request_reason': reason,
            })
            order.message_post(
                body='📱 Customer requested CANCELLATION of this paid '
                     'order from the app.%s' % (
                         ' Reason: %s' % reason if reason else ''))
            try:
                request.env.cr.commit()
            except Exception:
                pass
            return ok({'result': 'requested'})
        # unpaid (or still a draft cart) → cancel right away
        try:
            order.with_context(disable_cancel_warning=True).action_cancel()
        except Exception:
            order.state = 'cancel'
        if order.state != 'cancel':
            order.state = 'cancel'
        order.message_post(body='📱 Cancelled by the customer from the '
                                'app.%s' % (' Reason: %s' % reason
                                            if reason else ''))
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'result': 'cancelled'})

    @http.route('/api/mobile/v2/orders/shipping-methods', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def shipping_methods(self, **kw):
        order = _get_or_create_order(create=False)
        if not order:
            return ok([_cod_carrier_dict()])
        # Selective checkout: rate against ONLY the selected lines so the
        # picker shows exactly what will be charged (free-shipping
        # thresholds re-judged on the paid subset).
        sel = selected_line_ids(kw)
        if sel:
            return subset_view(order, sel,
                               lambda: self._shipping_methods_for(order))
        return self._shipping_methods_for(order)

    def _shipping_methods_for(self, order):
        # Build a permissive carrier list — three rounds of fallback so
        # the picker is never empty:
        #   1. Published + scoped to this website (or universal)
        #   2. Published universal-only (drop website match)
        #   3. ALL active carriers
        # Always append a synthetic "Cash on Delivery" entry so the
        # customer can pick at-door cash even if no carrier is set up.
        website = get_website()
        Carrier = request.env['delivery.carrier'].sudo()
        carriers = Carrier
        if website:
            carriers = Carrier.search([
                ('is_published', '=', True), ('active', '=', True),
                '|', ('website_id', '=', False),
                     ('website_id', '=', website.id)])
        if not carriers:
            carriers = Carrier.search([
                ('is_published', '=', True), ('active', '=', True),
                ('website_id', '=', False)])
        if not carriers:
            carriers = Carrier.search([('active', '=', True)])

        # Unified delivery filter — website / destination country / channel
        # / weekly schedule / vendor gating (delivery_carrier_portal).
        try:
            _cc = ''
            ship_to = order.partner_shipping_id or order.partner_id
            if ship_to and ship_to.country_id:
                _cc = ship_to.country_id.code or ''
            carriers = carriers.filtered(
                lambda c: not hasattr(c, 'available_for_order')
                or c.available_for_order(order, website=website,
                                         country_code=_cc, channel='app'))
        except Exception:
            pass

        out = []
        seen_names = set()
        for c in carriers:
            price = None
            zone = None
            if 'uellow_zone_ids' in c._fields and c.uellow_zone_ids:
                try:
                    z = request.env['uellow.delivery.zone'].sudo().quote_for(
                        c, order.partner_shipping_id or order.partner_id)
                    if z:
                        price = z.price
                        zone = {'name': z.name, 'cutoff_time': z.cutoff_time or ''}
                except Exception:
                    pass
            if price is None:
                try:
                    r = c.rate_shipment(order)
                    if isinstance(r, dict) and r.get('success'):
                        price = r.get('price', 0)
                except Exception:
                    # Fixed-type with no fixed_price still has it on the field
                    price = getattr(c, 'fixed_price', None)
            if price is None:
                price = getattr(c, 'fixed_price', None) or 0
            # Dedupe by translated name (avoids 7× "Bosta Delivery")
            # v2.1.18 — customer-facing label override + small description
            # (delivery_carrier_portal unified fields).
            name_dict = bilingual(c, 'name')
            if getattr(c, 'public_label_en', '') or getattr(c, 'public_label_ar', ''):
                name_dict = {
                    'en': c.public_label_en or name_dict.get('en') or '',
                    'ar': c.public_label_ar or c.public_label_en
                          or name_dict.get('ar') or '',
                }
            desc_dict = None
            if getattr(c, 'public_desc_en', '') or getattr(c, 'public_desc_ar', ''):
                desc_dict = {
                    'en': c.public_desc_en or '',
                    'ar': c.public_desc_ar or c.public_desc_en or '',
                }
            label_key = (name_dict.get('en') or '').strip().lower()
            if label_key in seen_names:
                continue
            seen_names.add(label_key)
            # delivery.carrier has no image field in Odoo 18 — the icon
            # lives on the linked product.product. Fall back gracefully.
            logo = None
            try:
                if c.product_id and c.product_id.image_128:
                    logo = img_url('product.product', c.product_id.id,
                                   'image_128', unique=c.product_id.write_date)
            except Exception:
                pass
            # v2.1.51 — unified free-shipping engine (product flags /
            # threshold / coupon / carrier free-over; express excluded).
            price, free_label = effective_shipping_price(order, c, price)
            # v2.1.55 — schedule/cutoff awareness for the picker (the
            # express row shows a clear "unavailable now" marker).
            now_ok, now_note = _carrier_now_availability(c)
            out.append({
                'id': c.id,
                'name': name_dict,
                'description': desc_dict,
                'price': fmt_price(price, order.currency_id),
                'is_free': free_label is not None,
                'free_label': free_label,
                'available_now': now_ok,
                'availability_note': now_note,
                'is_express': carrier_is_express(c),
                'is_default': c.is_default if 'is_default' in c._fields else False,
                'zone': zone,
                'logo': logo,
            })
        # v2.1.21 — the synthetic "Standard Delivery" (id=-1, price 0) is
        # ONLY a fallback for when no real carrier matched; with real
        # carriers configured it confused customers (free-looking option).
        if not out:
            out.append(_cod_carrier_dict(order=order))
        return ok(out)

    @http.route('/api/mobile/v2/orders/delivery-eta', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def delivery_eta(self, **kw):
        """Product-page delivery block: per-carrier availability NOW vs
        the next available day, computed from the unified weekly schedule
        (delivery_carrier_portal). Example: a carrier that skips Friday,
        asked on Thursday evening → "order now, receive Saturday"."""
        from datetime import datetime, timedelta
        import pytz
        website = get_website()
        country = (kw.get('country')
                   or request.httprequest.headers.get('CF-IPCountry')
                   or '').upper().strip()

        DAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                   'Friday', 'Saturday', 'Sunday']
        DAYS_AR = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس',
                   'الجمعة', 'السبت', 'الأحد']
        tz = pytz.timezone(request.env.user.tz or 'Asia/Kuwait')
        now = datetime.now(tz)

        def scope_ok(c):
            """Website/country/channel/date scope — WITHOUT the time check
            (we need out-of-hours carriers too, to compute their next slot)."""
            if getattr(c, 'uellow_channel', 'both') not in ('both', 'app'):
                return False
            ws = getattr(c, 'uellow_website_ids', None)
            if ws and website and website.id not in ws.ids:
                return False
            cs = getattr(c, 'uellow_country_ids', None)
            if cs and country and country not in [x.code for x in cs]:
                return False
            if getattr(c, 'vendor_id', False):
                return False     # vendor methods are cart-specific
            df = getattr(c, 'uellow_date_from', False)
            dt_ = getattr(c, 'uellow_date_to', False)
            today = now.date()
            if df and today < df:
                return False
            if dt_ and today > dt_:
                return False
            return True

        def next_slot(c):
            """(is_now, day_offset, day_name_en, day_name_ar, from_hour).
            Empty schedule = always available now."""
            avail = getattr(c, 'availability_ids', None)
            if not avail:
                return True, 0, '', '', 0.0
            hour = now.hour + now.minute / 60.0
            for off in range(0, 8):
                wd = (now.weekday() + off) % 7
                wins = [a for a in avail if int(a.weekday) == wd]
                for a in sorted(wins, key=lambda x: x.hour_from):
                    if off == 0:
                        if a.hour_from <= hour < a.hour_to:
                            return True, 0, '', '', 0.0
                        if hour < a.hour_from:
                            return False, 0, DAYS_EN[wd], DAYS_AR[wd], a.hour_from
                    else:
                        return False, off, DAYS_EN[wd], DAYS_AR[wd], a.hour_from
            return False, -1, '', '', 0.0

        Carrier = request.env['delivery.carrier'].sudo()
        carriers = Carrier.search([
            ('is_published', '=', True), ('active', '=', True)])
        lines = []
        for c in carriers:
            if not scope_ok(c):
                continue
            name = {
                'en': getattr(c, 'public_label_en', '') or c.name,
                'ar': getattr(c, 'public_label_ar', '')
                      or getattr(c, 'public_label_en', '') or c.name,
            }
            desc_en = getattr(c, 'public_desc_en', '') or ''
            desc_ar = getattr(c, 'public_desc_ar', '') or desc_en
            is_now, off, den, dar, fh = next_slot(c)
            # Cutoff from the carrier's zone rules when configured.
            cutoff = ''
            try:
                z = c.uellow_zone_ids[:1] if getattr(
                    c, 'uellow_zone_ids', False) else None
                cutoff = (z.cutoff_time or '') if z else ''
            except Exception:
                pass
            # v2.1.35 — ENFORCE the cutoff: a carrier whose schedule says
            # "open" but whose order cutoff already passed (express ends
            # 21:00, it's 23:00) is NOT available now — it ships tomorrow.
            if is_now and cutoff:
                try:
                    # tolerate "21" as well as "21:00"
                    parts = (cutoff.split(':') + ['0'])[:2] \
                        if ':' in cutoff else [cutoff, '0']
                    ch, cm = parts
                    if (now.hour * 60 + now.minute) >= \
                            (int(ch) * 60 + int(cm)):
                        is_now, off = False, 1
                        wd = (now.weekday() + 1) % 7
                        den, dar = DAYS_EN[wd], DAYS_AR[wd]
                        fh = 0.0
                except Exception:
                    pass
            # Extra facts for the delivery details dialog (v2.1.35).
            extra = {'cutoff': cutoff}
            try:
                if c.delivery_type == 'fixed':
                    extra['price'] = float(c.fixed_price or 0)
                if getattr(c, 'free_over', False):
                    extra['free_over'] = float(getattr(c, 'amount', 0) or 0)
            except Exception:
                pass
            if is_now:
                txt_en = desc_en or (
                    ('Available now — order before %s' % cutoff)
                    if cutoff else 'Available now')
                txt_ar = desc_ar or (
                    ('متاح الآن — اطلب قبل %s' % cutoff)
                    if cutoff else 'متاح الآن')
                lines.append(dict(extra, name=name, status='now',
                              text={'en': txt_en, 'ar': txt_ar}))
            elif off >= 0:
                hh = '%02d:%02d' % (int(fh), round((fh % 1) * 60))
                if off == 0:
                    txt_en = 'Opens today at %s' % hh
                    txt_ar = 'يبدأ اليوم الساعة %s' % hh
                elif off == 1:
                    if cutoff and not fh:
                        txt_en = ("Today's cutoff (%s) passed — "
                                  'delivers tomorrow (%s)') % (cutoff, den)
                        txt_ar = ('انتهى وقت الطلب اليوم (%s) — '
                                  'التوصيل غداً (%s)') % (cutoff, dar)
                    else:
                        txt_en = 'Order now — receive tomorrow (%s)' % den
                        txt_ar = 'اطلب الآن واستلم غداً (%s)' % dar
                else:
                    txt_en = 'Order now — receive on %s' % den
                    txt_ar = 'اطلب الآن واستلم يوم %s' % dar
                lines.append(dict(extra, name=name, status='later',
                              text={'en': txt_en, 'ar': txt_ar}))
        # "now" carriers first, then soonest
        lines.sort(key=lambda l: 0 if l['status'] == 'now' else 1)
        return ok({'country': country, 'lines': lines[:4]})

    @http.route('/api/mobile/v2/orders/checkout/geoip', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def checkout_geoip(self, **kw):
        """Detect city/country from the request IP + return whether any
        stored address matches that location. Used to pre-select an
        address (or suggest adding one) on the checkout screen."""
        ip = request.httprequest.remote_addr or ''
        cf_country = (request.httprequest.headers.get('CF-IPCountry') or '').upper() or None
        city = None
        country = cf_country
        try:
            geo = request.env['res.country'].sudo()._geoip_resolve(ip)
            if isinstance(geo, dict):
                country = (geo.get('country_code') or country)
                city = geo.get('city')
        except Exception:
            pass

        # Find a matching stored address if user is logged in
        suggested = None
        partner = current_partner()
        if partner and city:
            match = request.env['res.partner'].sudo().search([
                '|', ('id', '=', partner.id),
                     ('parent_id', '=', partner.id),
                ('city', 'ilike', city),
            ], limit=1)
            if match:
                suggested = _addr_dict(match)

        return ok({
            'ip': ip,
            'country': country,
            'city': city,
            'matched_address': suggested,
        })

    @http.route('/api/mobile/v2/orders/payment-methods', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def payment_methods(self, **kw):
        # Country-aware payment method picker. Resolution order:
        #   1. Explicit ?country=KW query param (from the app's country picker)
        #   2. Current website's mapped country (mobile_country_website table)
        #   3. Cloudflare CF-IPCountry header
        #   4. Logged-in partner's billing country
        # Once we have a country, we look up the country's website_id from
        # the country→website map and use it to scope providers. Then we
        # always add COD as a universal fallback.
        p = get_payload()
        explicit = (p.get('country') or '').upper().strip()
        cf_country = (request.httprequest.headers.get('CF-IPCountry') or '').upper()
        country_code = explicit or cf_country
        try:
            partner = current_partner()
        except Exception:
            partner = None
        if not country_code and partner and partner.country_id:
            country_code = (partner.country_id.code or '').upper()
        # Look up the website for this country
        target_website = False
        if country_code:
            try:
                Map = request.env['mobile.country.website'].sudo()
                m = Map.search([('country_id.code', '=', country_code)], limit=1)
                if m and m.website_id:
                    target_website = m.website_id
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning('country->website lookup failed: %s', e)
        # Fall back to current website if country didn't resolve a mapping
        website = target_website or (
            get_website())
        domain = [('state', 'in', ['enabled', 'test'])]
        Provider = request.env['payment.provider'].sudo()
        providers = Provider
        if website:
            providers = Provider.search(
                domain + ['|', ('website_id', '=', False),
                              ('website_id', '=', website.id)])
        if not providers:
            providers = Provider.search(domain + [('website_id', '=', False)])
        if not providers:
            providers = Provider.search(domain)
        # ── Curated list: Cash on Delivery + UPayments methods ──────────
        # The DB has accumulated many duplicate manual providers; the app only
        # needs a clean set. Online card methods (KNET / Visa·Mastercard /
        # Apple Pay / Google Pay) all route through the real UPayments provider
        # (the checkout-confirm redirect to /shop/payment lets UPayments handle
        # the actual charge), and COD stays a direct option.
        def _name_lc(prov):
            try:
                return (prov.with_context(lang='en_US').name or '').lower()
            except Exception:
                raw = prov.name
                return (raw.get('en_US', '') if isinstance(raw, dict) else (raw or '')).lower()

        cod_prov = upay_prov = None
        for prov in providers:
            nm = _name_lc(prov)
            if upay_prov is None and (prov.code == 'upayments' or 'upayments' in nm):
                upay_prov = prov
            if cod_prov is None and ('cash on delivery' in nm or nm.strip() == 'cod'):
                cod_prov = prov

        curated = []
        if cod_prov:
            curated.append({
                'id': cod_prov.id, 'code': 'cod', 'provider_code': cod_prov.code,
                'name': {'en': 'Cash on Delivery', 'ar': 'الدفع عند الاستلام'},
                'image': None, 'is_default': False,
            })
        if upay_prov:
            upay_logo = (img_url('payment.provider', upay_prov.id, 'image_128',
                                 unique=upay_prov.write_date) if upay_prov.image_128 else None)
            subs = [
                ('knet',       {'en': 'KNET',               'ar': 'كي نت'}),
                ('card',       {'en': 'Visa / Mastercard',  'ar': 'فيزا / ماستركارد'}),
                ('apple_pay',  {'en': 'Apple Pay',          'ar': 'Apple Pay'}),
                ('google_pay', {'en': 'Google Pay',         'ar': 'Google Pay'}),
            ]
            for idx, (code, nm) in enumerate(subs):
                curated.append({
                    # Synthetic unique id for UI selection; confirm routes by `code`
                    # (any non-cod code → online → /shop/payment → UPayments).
                    'id': -(900 + idx),
                    'code': code, 'provider_code': 'upayments',
                    'name': nm, 'image': upay_logo, 'is_default': idx == 0,
                    'via_upayments': True,
                })
        if curated:
            # COD always last so an online method is the default selection.
            curated.sort(key=lambda m: m['code'] == 'cod')
            return ok(curated)

        # ── Fallback (no curated providers found) — legacy enumeration ──
        out = []
        seen_ui_codes = set()
        for prov in providers:
            # Convert the underlying provider code to a UI-friendly code
            # the Flutter side can map to icons / labels.
            ui_code = prov.code or ''
            # `prov.name` resolves to the translated string in the current
            # request language. Make sure we have lowercase English text
            # for matching by falling back to the EN value when needed.
            raw = prov.name
            if isinstance(raw, dict):
                name_lc = (raw.get('en_US') or raw.get('en') or '').lower()
            else:
                name_lc = (raw or '').lower()
            # Always check the en_US value too — when the request is in AR
            # the .name resolves to Arabic which won't match the elif chain.
            try:
                en_raw = prov.with_context(lang='en_US').name or ''
                name_lc = (name_lc + ' ' + en_raw.lower()).strip()
            except Exception:
                pass
            if 'vodafone' in name_lc:
                ui_code = 'vodafone_cash'
            elif 'cash on delivery' in name_lc or 'cod' in name_lc:
                ui_code = 'cod'
            elif 'knet' in name_lc:
                ui_code = 'knet'
            elif 'mada' in name_lc:
                ui_code = 'mada'
            elif 'stc' in name_lc:
                ui_code = 'stc_pay'
            elif 'naps' in name_lc:
                ui_code = 'naps'
            elif 'omannet' in name_lc or 'oman net' in name_lc:
                ui_code = 'omannet'
            elif 'benefit' in name_lc:
                ui_code = 'benefit'
            elif 'fawry' in name_lc:
                ui_code = 'fawry'
            elif 'tamara' in name_lc:
                ui_code = 'tamara'
            elif 'wire' in name_lc or 'bank' in name_lc:
                ui_code = 'bank'
            elif 'paypal' in name_lc:
                ui_code = 'paypal'
            elif 'tabby' in name_lc:
                ui_code = 'tabby'
            elif 'taly' in name_lc:
                ui_code = 'taly'
            elif 'apple' in name_lc:
                ui_code = 'apple_pay'
            elif 'upayments' in name_lc:
                ui_code = 'upayments'
            elif 'visa' in name_lc or 'master' in name_lc or 'card' in name_lc:
                ui_code = 'card'
            # Dedupe by UI code so we don't show 2× COD or 2× UPayments
            # when both a country-specific row AND a universal row exist.
            if ui_code in seen_ui_codes:
                continue
            seen_ui_codes.add(ui_code)
            out.append({
                'id': prov.id,
                'name': bilingual(prov, 'name'),
                'code': ui_code,
                'provider_code': prov.code,
                'image': img_url('payment.provider', prov.id, 'image_128',
                                 unique=prov.write_date) if prov.image_128 else None,
                'is_default': bool(prov.is_published),
            })
        # If no providers were configured at all, add a Cash on Delivery
        # fallback so the customer can still place an order.
        if not out:
            out.append({
                'id': -1,
                'name': {'en': 'Cash on Delivery', 'ar': 'الدفع عند الاستلام'},
                'code': 'cod', 'provider_code': 'custom',
                'image': None, 'is_default': True,
            })
        return ok(out)

    @http.route('/api/mobile/v2/orders/checkout/summary', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def checkout_summary(self, **kw):
        partner, err = _guest_gate(kw)
        if err:
            return err
        order = _get_or_create_order(create=False)
        if not order or not order.order_line:
            return fail('EMPTY_CART', 'Cart is empty', 400)
        # Re-evaluate coupon rewards in case prices/qty changed since the
        # cart was last viewed. Without this, the reward line keeps the
        # discount it had at apply-time which can be stale relative to
        # checkout totals — which is the visible "coupon doesn't discount"
        # bug. _update_programs_and_rewards is the canonical recompute
        # entry-point in Odoo 17/18 loyalty.
        try:
            if hasattr(order, '_update_programs_and_rewards'):
                order._update_programs_and_rewards()
        except Exception:
            pass
        if partner:
            addrs = request.env['res.partner'].sudo().search([
                ('parent_id', '=', partner.id),
                ('type', 'in', ('delivery', 'invoice')),
            ], order='is_default_shipping desc, create_date desc')
            addr_list = [_addr_dict(a) for a in addrs] + [_addr_dict(partner)]
        else:
            # Guest — the ad-hoc partner created by the guest address flow
            # (skip while the order still belongs to the public user).
            ship = order.partner_shipping_id
            public_partners = request.env['website'].sudo().search([]) \
                .mapped('user_id.partner_id').ids
            addr_list = ([_addr_dict(ship)]
                         if ship and ship.id not in public_partners else [])
        # Selective checkout: show totals for ONLY the selected lines.
        sel = selected_line_ids(kw)
        cart_json = subset_view(order, sel, lambda: serialize_cart(order)) \
            if sel else serialize_cart(order)
        return ok({
            'cart': cart_json,
            'addresses': addr_list,
        })

    @http.route('/api/mobile/v2/orders/checkout/confirm', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def checkout_confirm(self, **kw):
        p = get_payload()
        partner, err = _guest_gate(p)
        if err:
            return err
        order = _get_or_create_order(create=False)
        if not order or not order.order_line:
            return fail('EMPTY_CART', 'Cart is empty', 400)

        # Selective checkout (v2.1.65): pay for ONLY the selected lines.
        # The unselected lines move to a fresh draft order that becomes
        # the customer's cart; everything below (shipping, coupons,
        # payment, webhooks) runs unchanged on the reduced order.
        sel = selected_line_ids(p)
        if sel:
            try:
                split_cart_for_checkout(order, sel)
            except ValueError:
                return fail('BAD_SELECTION',
                            'Selected items are no longer in the cart — '
                            'refresh and try again / المنتجات المحددة لم '
                            'تعد في السلة، حدّث السلة وحاول مجدداً', 400)
            except Exception as e:
                return fail('SPLIT_FAILED', str(e), 400)

        # Apply chosen addresses
        try:
            if p.get('delivery_address_id'):
                order.partner_shipping_id = int(p['delivery_address_id'])
            if p.get('invoice_address_id'):
                order.partner_invoice_id = int(p['invoice_address_id'])
        except Exception:
            pass

        # Resolve the chosen carrier + shipping rate WITHOUT persisting a
        # delivery line yet. Persisting it on a draft cart was the bug: it
        # showed shipping as a cart "product" and got double-counted at
        # checkout. The delivery line is added only when the order is actually
        # placed (COD now, or online after payment capture).
        carrier = None
        ship_rate = 0.0
        try:
            cid = int(p.get('carrier_id') or 0)
            if cid > 0:
                carrier = request.env['delivery.carrier'].sudo().browse(cid)
                if not carrier.exists():
                    carrier = None
        except Exception:
            carrier = None
        if carrier is not None and hasattr(carrier, 'available_for_order'):
            try:
                _cc2 = ''
                _st = order.partner_shipping_id or order.partner_id
                if _st and _st.country_id:
                    _cc2 = _st.country_id.code or ''
                if not carrier.available_for_order(
                        order, website=get_website(),
                        country_code=_cc2, channel='app'):
                    return fail('CARRIER_UNAVAILABLE',
                                'This delivery method is not available right '
                                'now — pick another one / وسيلة التوصيل غير '
                                'متاحة حالياً، اختر وسيلة أخرى', 400)
            except Exception:
                pass
        if carrier is not None:
            # Resolve the price with the SAME fallback chain the picker
            # (shipping-methods endpoint) uses, so the charged shipping always
            # matches what the customer saw: zone quote → rate_shipment (only
            # when success) → fixed_price. rate_shipment alone returns
            # success=False/price=0 for out-of-zone addresses even though the
            # picker displayed a real price.
            price = None
            if 'uellow_zone_ids' in carrier._fields and carrier.uellow_zone_ids:
                try:
                    z = request.env['uellow.delivery.zone'].sudo().quote_for(
                        carrier, order.partner_shipping_id or order.partner_id)
                    if z:
                        price = z.price
                except Exception:
                    pass
            if price is None:
                try:
                    rr = carrier.rate_shipment(order)
                    if isinstance(rr, dict) and rr.get('success'):
                        price = rr.get('price', 0)
                except Exception:
                    pass
            if price is None:
                price = getattr(carrier, 'fixed_price', None) or 0
            # v2.1.51 — the engine decides the FINAL charged rate so the
            # invoice always matches the picker (free stays free).
            price, _free_lbl = effective_shipping_price(order, carrier, price)
            ship_rate = float(price or 0.0)
            try:
                order.carrier_id = carrier.id   # remember the choice
            except Exception:
                pass

        # Guests must have provided a delivery address (the guest address
        # flow attaches an ad-hoc partner to the order).
        if not partner:
            public_partners = request.env['website'].sudo().search([]) \
                .mapped('user_id.partner_id').ids
            ship = order.partner_shipping_id
            if not ship or ship.id in public_partners:
                return fail('ADDRESS_REQUIRED',
                            'Add a delivery address first / أضف عنوان التوصيل '
                            'أولاً', 400)

        pm = (p.get('payment_method') or '').lower()
        cod = pm == 'cod'

        if cod:
            # Place now: add the delivery line (preserving reward lines) + confirm.
            if carrier is not None:
                _apply_delivery_preserving_rewards(order, carrier, ship_rate)
            try:
                order.action_confirm()
            except Exception as e:
                return fail('CONFIRM_FAILED', str(e), 400)

        result = {
            'order_id': order.id,
            'order_name': order.name,
            'payment_required': not cod,
        }
        # v2.1.21 — online-payment cashback teaser (credited on capture by
        # the payment webhook; cash orders earn nothing).
        if not cod and partner:
            try:
                setting = app_setting()
                cb = setting.cashback_for(
                    (order.amount_total or 0.0) + (ship_rate or 0.0)) \
                    if setting else 0.0
                if cb > 0:
                    result['cashback'] = {
                        'amount': cb,
                        'currency': order.currency_id.name or 'KWD',
                    }
            except Exception:
                pass
        if not cod:
            base = base_url().rstrip('/')
            gateway = {'knet': 'knet', 'card': 'cc', 'apple_pay': 'apple-pay',
                       'google_pay': 'google-pay'}.get(pm)
            # Charge total INCLUDES shipping (the draft order has no delivery
            # line so amount_total excludes it). Stash the rate so the webhook
            # can add the delivery line when it confirms on capture.
            charge_amount = round((order.amount_total or 0.0) + (ship_rate or 0.0), 3)
            try:
                order.sudo().write({'upayments_ship_rate': ship_rate})
            except Exception:
                pass
            if hasattr(order, '_upayments_create_charge'):
                try:
                    result['payment_url'] = order._upayments_create_charge(
                        return_url='%s/payments/upayments/return' % base,
                        cancel_url='%s/payments/upayments/cancel' % base,
                        notify_url='%s/payments/upayments/webhook' % base,
                        lang=get_lang(), gateway=gateway, amount=charge_amount)
                except Exception as e:
                    return fail('PAYMENT_INIT_FAILED', str(e), 400)
            else:
                result['payment_url'] = f"{base}/shop/payment?order_id={order.id}"
        return ok(result)


    @http.route('/api/mobile/v2/orders/<int:order_id>/invoice', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_invoice_pdf(self, order_id, **kw):
        """Return the invoice PDF for this order. If no invoice exists
        yet, lazily render the sale.order quotation report so the
        customer can always download something."""
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)
        report = None
        pdf_bytes = None
        try:
            invoices = order.invoice_ids.filtered(lambda m: m.state != 'cancel')
            if invoices:
                report_ref = 'account.account_invoices'
                report = request.env.ref(report_ref, raise_if_not_found=False).sudo()
                if report:
                    pdf_bytes, _t = report._render_qweb_pdf(report_ref, res_ids=invoices.ids)
            if not pdf_bytes:
                # Fallback — render the order/quotation report
                report_ref = 'sale.action_report_saleorder'
                report = request.env.ref(report_ref, raise_if_not_found=False).sudo()
                if report:
                    pdf_bytes, _t = report._render_qweb_pdf(report_ref, res_ids=order.ids)
        except Exception as e:
            return fail('REPORT_FAIL', str(e), 500)
        if not pdf_bytes:
            return fail('NO_INVOICE', 'No invoice available', 404)
        filename = f'{order.name.replace("/", "-")}.pdf'
        return request.make_response(pdf_bytes, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'inline; filename="{filename}"'),
            ('Content-Length', str(len(pdf_bytes))),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/api/mobile/v2/orders/<int:order_id>/contact-seller', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def contact_seller(self, order_id, **kw):
        """Open a helpdesk ticket against the seller (vendor) of this
        order, on behalf of the customer."""
        p = get_payload()
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)
        subject = (p.get('subject') or
                   f'Question about order {order.name}').strip()
        body = (p.get('body') or p.get('message') or '').strip()
        if not body:
            return fail('EMPTY', 'Message body required', 400)
        # Vendor partner — pull from order line if present.
        vendor = False
        for line in order.order_line:
            v = getattr(line.product_id, 'vendor_id', False)
            if v:
                vendor = v
                break
        Team = request.env['helpdesk.team'].sudo()
        team = Team.search([], limit=1) if 'helpdesk.team' in request.env else False
        Ticket = request.env['helpdesk.ticket'].sudo() if 'helpdesk.ticket' in request.env else None
        ticket_id = None
        if Ticket and team:
            vals = {
                'name': subject,
                'description': body + (
                    f'\n\n— From mobile app, order {order.name}'),
                'partner_id': partner.id,
                'partner_email': partner.email or '',
                'partner_name': partner.name or '',
                'team_id': team.id,
            }
            if vendor:
                vals['user_id'] = vendor.user_ids[:1].id if vendor.user_ids else False
            try:
                t = Ticket.create(vals)
                ticket_id = t.id
                # Optional photo attachments (max 5)
                photos = p.get('photos') or p.get('images') or []
                if isinstance(photos, str):
                    try:
                        import json as _json
                        photos = _json.loads(photos)
                    except Exception:
                        photos = []
                if isinstance(photos, list):
                    for idx, b64 in enumerate(photos[:5]):
                        if not b64:
                            continue
                        if isinstance(b64, str) and b64.startswith('data:') and ',' in b64:
                            b64 = b64.split(',', 1)[1]
                        try:
                            request.env['ir.attachment'].sudo().create({
                                'name': f'ticket-{t.id}-photo-{idx+1}.jpg',
                                'type': 'binary',
                                'datas': b64,
                                'res_model': 'helpdesk.ticket',
                                'res_id': t.id,
                                'mimetype': 'image/jpeg',
                            })
                        except Exception:
                            pass
            except Exception:
                pass
        return ok({'ticket_id': ticket_id,
                   'message': {'en': 'Message sent to seller',
                                'ar': 'تم إرسال رسالتك للبائع'}})

    @http.route('/api/mobile/v2/orders/<int:order_id>/refresh', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_refresh(self, order_id, **kw):
        """Same as detail — separate route so the app can show a
        spinner labelled 'Refreshing…' explicitly."""
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)
        return ok({'order': serialize_order(order, detail=True)})


def _cod_carrier_dict(order=None):
    cur = (order.currency_id if order else request.env.company.currency_id)
    # Plain "Standard Delivery" (no COD-available suffix); when the cart
    # already qualifies for free shipping, label it "Free delivery" instead.
    name = {'en': 'Standard Delivery', 'ar': 'توصيل قياسي'}
    try:
        from .cart import _free_shipping_threshold
        threshold = _free_shipping_threshold(order) if order else None
        if threshold and order and order.amount_untaxed >= threshold:
            name = {'en': 'Free delivery', 'ar': 'توصيل مجاني'}
    except Exception:
        pass
    return {
        'id': -1,
        'name': name,
        'price': fmt_price(0, cur),
        'is_default': False,
        'zone': None,
        'logo': None,
        'is_cod_fallback': True,
    }


def _addr_dict(p):
    return {
        'id': p.id,
        'name': p.name,
        'phone': p.phone or p.mobile or '',
        'street': p.street or '',
        'street2': p.street2 or '',
        'city': p.city or '',
        'state_id': p.state_id.id if p.state_id else None,
        'state': p.state_id.name if p.state_id else '',
        'country_id': p.country_id.id if p.country_id else None,
        'country': p.country_id.name if p.country_id else '',
        'zip': p.zip or '',
        'type': p.type or 'contact',
        'is_default': bool(getattr(p, 'is_default_shipping', False)),
    }
