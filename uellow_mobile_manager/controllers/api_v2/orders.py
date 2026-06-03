"""
Orders & checkout — /api/mobile/v2/orders/*

list                GET   /                          → user's orders
detail              GET   /<id>                       → one order
shipping_methods    GET   /shipping-methods           → available methods for cart
payment_methods     GET   /payment-methods            → available providers
checkout_summary    GET   /checkout/summary           → totals + addresses + methods
checkout_confirm    POST  /checkout/confirm           → place order, returns payment URL or order
"""
from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    img_url, base_url, fmt_price, bilingual, get_lang,
)
from .cart import _get_or_create_order, serialize_cart


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
    setting = request.env['mobile.app.setting'].sudo().search([], limit=1)
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
        'at_carrier':   {'en': 'At delivery hub',        'ar': 'في مركز التوصيل'},
        'in_transit':   {'en': 'Driver on the way',      'ar': 'السائق في الطريق'},
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
                'ar': 'في الطريق · يصل قريباً'}
    if ds == 'assigned':
        return {'en': 'Driver assigned · awaiting pickup',
                'ar': 'تم تعيين السائق · بانتظار الاستلام'}
    if ds == 'delivered':
        return {'en': 'Delivered', 'ar': 'تم التسليم'}
    if ds == 'arrived_sorting':
        return {'en': 'At sorting center', 'ar': 'في مركز الفرز'}
    return {'en': 'Order placed', 'ar': 'تم استلام الطلب'}


def _order_timeline(order):
    """Per-step timeline used by the tracking screen — every Uellow
    status with done/current/upcoming markers."""
    current = _uellow_status(order)['code']
    cur_idx = _UELLOW_STATUS_DICT[current]['idx']
    out = []
    # Show only the linear positive flow (skip cancelled/returned)
    for code in ('draft', 'confirmed', 'preparing', 'shipping', 'delivered'):
        meta = _UELLOW_STATUS_DICT[code]
        state = 'done' if meta['idx'] < cur_idx else (
            'current' if meta['idx'] == cur_idx else 'upcoming')
        # Special-case if we're at cancelled/returned, mark all upcoming
        if current in ('cancelled', 'returned'):
            state = 'done' if meta['idx'] <= 1 else 'upcoming'
        out.append({
            'code': code,
            'label': {'en': meta['en'], 'ar': meta['ar']},
            'state': state,
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

    @http.route('/api/mobile/v2/orders/shipping-methods', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def shipping_methods(self, **kw):
        order = _get_or_create_order(create=False)
        if not order:
            return ok([_cod_carrier_dict()])
        # Build a permissive carrier list — three rounds of fallback so
        # the picker is never empty:
        #   1. Published + scoped to this website (or universal)
        #   2. Published universal-only (drop website match)
        #   3. ALL active carriers
        # Always append a synthetic "Cash on Delivery" entry so the
        # customer can pick at-door cash even if no carrier is set up.
        website = (request.env['website'].get_current_website()
                    if hasattr(request.env['website'], 'get_current_website') else False)
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
            name_dict = bilingual(c, 'name')
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
            out.append({
                'id': c.id,
                'name': name_dict,
                'price': fmt_price(price, order.currency_id),
                'is_default': c.is_default if 'is_default' in c._fields else False,
                'zone': zone,
                'logo': logo,
            })
        # Always offer Cash on Delivery as a synthetic option — works as
        # both shipping + payment hint. id=-1 so the Flutter side can
        # detect and route to COD without a real carrier_id.
        out.append(_cod_carrier_dict(order=order))
        return ok(out)

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
            request.env['website'].get_current_website()
            if hasattr(request.env['website'], 'get_current_website') else False)
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
    @require_auth
    def checkout_summary(self, **kw):
        partner = current_partner()
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
        addrs = request.env['res.partner'].sudo().search([
            ('parent_id', '=', partner.id),
            ('type', 'in', ('delivery', 'invoice')),
        ], order='create_date desc')
        return ok({
            'cart': serialize_cart(order),
            'addresses': [_addr_dict(a) for a in addrs] + [_addr_dict(partner)],
        })

    @http.route('/api/mobile/v2/orders/checkout/confirm', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def checkout_confirm(self, **kw):
        p = get_payload()
        partner = current_partner()
        order = _get_or_create_order(create=False)
        if not order or not order.order_line:
            return fail('EMPTY_CART', 'Cart is empty', 400)

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
        if carrier is not None:
            try:
                rr = carrier.rate_shipment(order)
                ship_rate = (rr or {}).get('price', 0) if isinstance(rr, dict) else 0
            except Exception:
                ship_rate = 0.0
            try:
                order.carrier_id = carrier.id   # remember the choice
            except Exception:
                pass

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
    return {
        'id': -1,
        'name': {'en': 'Standard Delivery (COD available)',
                  'ar': 'توصيل قياسي — متاح الدفع عند الاستلام'},
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
