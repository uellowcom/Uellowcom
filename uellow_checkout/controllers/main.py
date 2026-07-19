# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)
_SKIP = {'paypal', 'wire_transfer'}


def _json_resp(data):
    body = json.dumps(data)
    return Response(body, status=200, headers=[
        ('Content-Type', 'application/json; charset=utf-8'),
        ('Content-Length', str(len(body.encode()))),
    ])


def _sym(order):
    try:
        return order.currency_id.symbol or order.currency_id.name or 'KD'
    except Exception:
        return 'KD'


def _lang():
    env_lang = (request.env.lang or '').lower()
    if env_lang.startswith('ar'):
        return 'ar'
    path = request.httprequest.path or ''
    if '/ar/' in path or path.endswith('/ar'):
        return 'ar'
    return 'en'


def _geo_str(obj):
    if obj is None:
        return ''
    if isinstance(obj, str):
        s = obj.strip()
        if 'geoip2' in s or '_locales' in s or s.startswith('<'):
            return ''
        return s
    name = getattr(obj, 'name', None)
    if name and isinstance(name, str):
        return name.strip()
    iso = getattr(obj, 'iso_code', None)
    if iso and isinstance(iso, str):
        return iso.strip()
    return ''


def _geoip():
    geo = {}
    try:
        gip   = request.geoip
        city  = _geo_str(getattr(gip, 'city', ''))
        state = _geo_str(getattr(gip, 'subdivision_1_name', '')) or _geo_str(getattr(gip, 'region', ''))
        cc    = _geo_str(getattr(gip, 'country_code', ''))
        lat   = getattr(gip, 'latitude',  None)
        lng   = getattr(gip, 'longitude', None)
        if lat is not None:
            try: lat = float(lat)
            except Exception: lat = None
        if lng is not None:
            try: lng = float(lng)
            except Exception: lng = None
        geo = {'city': city, 'state': state, 'country_code': cc, 'lat': lat, 'lng': lng}
        if cc:
            country = request.env['res.country'].sudo().search([('code', '=', cc)], limit=1)
            if country:
                geo['country_id'] = country.id
                if state:
                    s = request.env['res.country.state'].sudo().search(
                        [('country_id', '=', country.id), ('name', 'ilike', state[:20])], limit=1)
                    if s:
                        geo['state_id'] = s.id
    except Exception:
        pass
    return geo


def _save_uc_order(order, payment_method, env):
    try:
        partner = order.partner_id
        env['uc.order'].sudo().create({
            'name':           partner.name or '',
            'phone':          partner.phone or '',
            'email':          partner.email or '',
            'sale_order_id':  order.id,
            'partner_id':     partner.id,
            'payment_method': payment_method,
            'city':           partner.city or '',
            'street':         partner.street or '',
            'governorate':    partner.state_id.name if partner.state_id else '',
            'full_address':   (order.note or '').split(chr(10))[0].replace('Delivery: ', ''),
        })
    except Exception as e:
        _logger.warning('save_uc_order: %s', e)


# Reuse the APP's shipping engine so the storefront charges EXACTLY what the
# app does (zones + free-shipping by carrier-company threshold / free-over /
# coupon / flags). Defensive import: if the app module is absent we degrade to
# the simple rate→fixed resolver below.
try:
    from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import (
        effective_shipping_price as _app_effective_ship)
except Exception:
    _app_effective_ship = None
# Reuse the APP's express-availability policy (weekly schedule + zone working
# hours + order cutoff) so the storefront shows the SAME "unavailable now"
# state, note and cutoff line as the app.
try:
    from odoo.addons.uellow_mobile_manager.controllers.api_v2.orders import (
        _carrier_now_availability as _app_carrier_avail)
except Exception:
    _app_carrier_avail = None


def _uc_zone_for(carrier, order):
    """The matched Uellow delivery zone for this carrier + destination (or
    None) — used for the cutoff line and the availability policy."""
    try:
        if 'uellow_zone_ids' in carrier._fields and carrier.uellow_zone_ids:
            return request.env['uellow.delivery.zone'].sudo().quote_for(
                carrier, order.partner_shipping_id or order.partner_id) or None
    except Exception:
        pass
    return None


def _uc_carrier_availability(carrier, order, lang):
    """(available_now, note_str, cutoff_str) matching the app exactly."""
    zone = _uc_zone_for(carrier, order)
    cutoff = ''
    try:
        cutoff = (zone.cutoff_time or '') if zone else ''
    except Exception:
        cutoff = ''
    if _app_carrier_avail is None:
        return True, '', cutoff
    try:
        ok, note = _app_carrier_avail(carrier, zone)
        note_str = ''
        if note:
            note_str = note.get('ar' if (lang or '').startswith('ar') else 'en', '') or ''
        return bool(ok), note_str, cutoff
    except Exception:
        return True, '', cutoff


def _uc_carrier_name(carrier, lang):
    """Customer-facing carrier name — the public label (EN/AR), exactly like
    the app. Falls back to the internal method name when no label is set."""
    ar = (lang or '').startswith('ar')
    try:
        if ar:
            return (carrier.public_label_ar or carrier.public_label_en
                    or carrier.name or '')
        return (carrier.public_label_en or carrier.public_label_ar
                or carrier.name or '')
    except Exception:
        return carrier.name or ''


def _uc_base_ship_price(carrier, order):
    """Base price BEFORE the free-shipping engine, resolved with the SAME
    chain the app uses: Uellow zone quote → rate_shipment (success only) →
    carrier fixed price. Never collapses to 0 on a transient rate failure."""
    price = None
    try:
        if 'uellow_zone_ids' in carrier._fields and carrier.uellow_zone_ids:
            z = request.env['uellow.delivery.zone'].sudo().quote_for(
                carrier, order.partner_shipping_id or order.partner_id)
            if z:
                price = float(z.price or 0.0)
    except Exception as e:
        _logger.warning('UC zone quote: %s', e)
    if price is None:
        try:
            rate = carrier.rate_shipment(order)
            if isinstance(rate, dict) and rate.get('success'):
                price = float(rate.get('price', 0.0) or 0.0)
        except Exception as e:
            _logger.warning('UC rate_shipment failed (%s)', e)
    if price is None:
        try:
            price = float(carrier.fixed_price or 0.0)
        except Exception:
            price = 0.0
    return price


def _uc_resolve_shipping(carrier, order):
    """(price, free_label) — the FINAL charged shipping, matching the app's
    engine. free_label is a {'en','ar'} dict when delivery is genuinely free,
    else None."""
    base = _uc_base_ship_price(carrier, order)
    free_label = None
    if _app_effective_ship is not None:
        try:
            base, free_label = _app_effective_ship(order, carrier, base)
        except Exception as e:
            _logger.warning('UC effective_shipping_price: %s', e)
    base = float(base or 0.0)
    # SHIP-GUARD: a non-free order must never confirm with 0 shipping.
    if free_label is None and base <= 0.0:
        try:
            fp = float(carrier.fixed_price or 0.0)
        except Exception:
            fp = 0.0
        if fp > 0.0:
            _logger.warning('SHIP-GUARD %s: rate 0 for non-free order — fixed %.3f',
                            order.name, fp)
            base = fp
    return base, free_label


def _uc_ship_price(carrier, order):
    """Just the charged price (for set_delivery_line)."""
    return _uc_resolve_shipping(carrier, order)[0]


try:
    from odoo.addons.website_sale.controllers.main import WebsiteSale as _WSBase
except ImportError:
    _WSBase = http.Controller


class UellowCheckout(_WSBase):

    # ── Cart update (live qty, returns accurate totals) ──────────────────────
    @http.route(['/uellow/cart_update'], type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def cart_update(self, **kw):
        """Update cart line qty and return accurate totals for live update."""
        line_id  = kw.get('line_id')
        quantity = kw.get('quantity')
        try:
            order = request.website.sale_get_order()
            if not order or line_id is None or quantity is None:
                return _json_resp({'success': False})
            lid = int(line_id)
            qty = int(quantity)
            line = request.env['sale.order.line'].sudo().browse(lid)
            if not line.exists() or line.order_id.id != order.id:
                return _json_resp({'success': False, 'error': 'line_not_found'})
            if qty <= 0:
                line.sudo().unlink()
            else:
                line.sudo().write({'product_uom_qty': qty})
            # Force recompute
            order.sudo()._compute_amount_all() if hasattr(order, '_compute_amount_all') else None
            order.sudo().invalidate_recordset()
            order = request.website.sale_get_order()  # re-fetch
            # Build per-line subtotals
            lines_data = []
            for l in order.sudo().order_line:
                if not l.is_delivery:
                    lines_data.append({
                        'id':       l.id,
                        'qty':      int(l.product_uom_qty),
                        'subtotal': round(float(l.price_subtotal), 3),
                    })
            # Cart shows product-only total (no delivery)
            product_total = round(sum(
                float(l.price_subtotal)
                for l in order.sudo().order_line
                if not l.is_delivery
            ), 3)
            return _json_resp({
                'success':  True,
                'removed':  qty <= 0,
                'subtotal': product_total,
                'total':    product_total,
                'lines':    lines_data,
            })
        except Exception as e:
            _logger.warning('cart_update: %s', e)
            return _json_resp({'success': False, 'error': str(e)})

    # ── Cart ─────────────────────────────────────────────────────────────────
    @http.route(['/shop/cart'], type='http', auth='public', website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        order    = request.website.sale_get_order()
        lang     = _lang()
        carriers = []
        try:
            carriers = request.env['delivery.carrier'].sudo().search(
                [('website_published', '=', True)])
        except Exception:
            pass
        return request.render('uellow_checkout.cart', {
            'order':           order,
            'uc_lang':         lang,
            'currency_symbol': _sym(order) if order else 'KD',
            'geo':             _geoip(),
            'carriers':        carriers,
        })

    # ── Checkout (address) ───────────────────────────────────────────────────
    @http.route(['/shop/checkout'], type='http', auth='public', website=True, sitemap=False)
    def checkout(self, country_id=None, zip=None, **post):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect('/shop/cart')
        lang  = _lang()
        geo   = _geoip()
        countries = request.env['res.country'].sudo().search([], order='name asc')
        sel_cid   = int(country_id) if country_id else (
            geo.get('country_id') or
            (order.partner_shipping_id.country_id.id if order.partner_shipping_id.country_id else False)
        )
        # Fallback: default to Kuwait if nothing resolved
        if not sel_cid:
            _kw = request.env['res.country'].sudo().search([('code', '=', 'KW')], limit=1)
            if _kw:
                sel_cid = _kw.id
        states = []
        if sel_cid:
            states = request.env['res.country.state'].sudo().search(
                [('country_id', '=', sel_cid)], order='name asc')
        carriers = []
        try:
            # Destination country for scoping (selected country → shipping
            # partner → KW fallback).
            dest_code = ''
            try:
                _country = request.env['res.country'].sudo().browse(sel_cid) \
                    if sel_cid else False
                dest_code = (_country.code or '') if _country else ''
            except Exception:
                dest_code = ''
            all_c = request.env['delivery.carrier'].sudo().search(
                [('website_published', '=', True)])
            for c in all_c:
                # Issue #2 fix — only offer carriers actually available on THIS
                # website + destination + channel. Previously every published
                # carrier showed (so e.g. SMSA/Bosta leaked into Kuwait).
                try:
                    if hasattr(c, 'available_for_order') and not c.available_for_order(
                            order, website=request.website,
                            country_code=dest_code, channel='website',
                            check_time=False):
                        continue
                except Exception:
                    pass
                # SHIP-GUARD + engine: picker price == charged price (zones +
                # free shipping). Issue #3 fix — show the public label name.
                price, free_label = _uc_resolve_shipping(c, order)
                _ar = lang.startswith('ar')
                _sub = ((c.public_desc_ar or c.public_desc_en) if _ar
                        else (c.public_desc_en or c.public_desc_ar)) or ''
                # Express-availability policy (same as the app): show out-of-
                # hours carriers dimmed with a note + cutoff line.
                avail_now, avail_note, cutoff = _uc_carrier_availability(c, order, lang)
                carriers.append({
                    'carrier':       c,
                    'price':         price,
                    'name':          _uc_carrier_name(c, lang),
                    'sub':           _sub,
                    'is_free':       free_label is not None,
                    'free_label':    (free_label.get('ar' if _ar else 'en')
                                      if isinstance(free_label, dict) else None),
                    'available_now': avail_now,
                    'avail_note':    avail_note,
                    'cutoff':        cutoff,
                })
        except Exception as e:
            _logger.warning('UC carriers: %s', e)
        return request.render('uellow_checkout.address', {
            'order':           order,
            'uc_lang':         lang,
            'currency_symbol': _sym(order),
            'geo':             geo,
            'countries':       countries,
            'states':          states,
            'selected_cid':    sel_cid,
            'carriers':        carriers,
            'saved_addresses': [],
        })

    # ── Save address ─────────────────────────────────────────────────────────
    @http.route(['/shop/checkout/address/save'], type='http', auth='public',
                website=True, sitemap=False, methods=['POST'], csrf=False)
    def save_address(self, **post):
        order = request.website.sale_get_order()
        if not order:
            return request.redirect('/shop/cart')
        name       = (post.get('name')       or '').strip()
        phone      = (post.get('phone')      or '').strip()
        email      = (post.get('email')      or '').strip()
        street     = (post.get('street')     or '').strip()
        city       = (post.get('city')       or '').strip()
        state_id   = post.get('state_id')
        country_id = post.get('country_id')
        lat        = (post.get('map_lat')    or '').strip()
        lng        = (post.get('map_lng')    or '').strip()
        full_addr  = (post.get('full_address') or '').strip()
        notes      = (post.get('order_notes')  or '').strip()
        penv  = request.env['res.partner'].sudo()
        pvals = {'name': name or 'Customer', 'phone': phone, 'customer_rank': 1,
                 'street': street, 'city': city}
        if email:    pvals['email'] = email
        if state_id:
            try:    pvals['state_id'] = int(state_id)
            except ValueError: pass
        if country_id:
            try:    pvals['country_id'] = int(country_id)
            except ValueError: pass
        existing = penv.search([('phone', '=', phone)], limit=1) if phone else None
        partner  = existing or penv.create(pvals)
        if existing:
            existing.write(pvals)
        order.write({
            'partner_id':          partner.id,
            'partner_invoice_id':  partner.id,
            'partner_shipping_id': partner.id,
        })
        carrier = None
        dest_code = (partner.country_id.code or '') if partner.country_id else ''
        carrier_id = post.get('carrier_id')
        if carrier_id:
            try:
                c = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
                if c.exists():
                    carrier = c
            except Exception:
                carrier = None
        # Express-availability policy: reject an out-of-hours selection (e.g.
        # express after closing) so it falls back to an open method below.
        if carrier is not None and hasattr(carrier, 'available_for'):
            try:
                if not carrier.available_for(website=request.website,
                                             country_code=dest_code,
                                             channel='website', check_time=True):
                    carrier = None
            except Exception:
                pass
        # Safety net — a customer must NEVER reach payment without a shipping
        # method. Default to the first carrier available NOW; if nothing is
        # open right now, fall back to any location-valid carrier so the order
        # still gets a correct shipping line.
        if carrier is None:
            try:
                published = request.env['delivery.carrier'].sudo().search(
                    [('website_published', '=', True)])
                for _ct in (True, False):
                    for c in published:
                        try:
                            if not hasattr(c, 'available_for_order') or c.available_for_order(
                                    order, website=request.website,
                                    country_code=dest_code, channel='website',
                                    check_time=_ct):
                                carrier = c
                                break
                        except Exception:
                            continue
                    if carrier is not None:
                        break
            except Exception as e:
                _logger.warning('default carrier: %s', e)
        if carrier is not None:
            try:
                # SHIP-GUARD + engine: zone/free-shipping aware price; never 0
                # on a glitch for a non-free order.
                order.sudo().set_delivery_line(carrier, _uc_ship_price(carrier, order))
            except Exception as e:
                _logger.warning('set_delivery_line: %s', e)
                try:    order._check_carrier_quotation(carrier)
                except Exception: order.sudo().write({'carrier_id': carrier.id})
        note_parts = []
        addr_detail = full_addr or ', '.join(filter(None, [street, city]))
        if addr_detail: note_parts.append('Delivery: ' + addr_detail)
        if lat and lng:  note_parts.append('Coords: %s,%s' % (lat, lng))
        note_parts.append('Payment: TBD')
        if notes:        note_parts.append('Notes: ' + notes)
        order.write({'note': chr(10).join(note_parts)})
        return request.redirect('/shop/payment')

    # ── Payment page ─────────────────────────────────────────────────────────
    @http.route(['/shop/payment'], type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return request.redirect('/shop/cart')
        lang = _lang()
        return request.render('uellow_checkout.payment', {
            'order':           order,
            'uc_lang':         lang,
            'currency_symbol': _sym(order),
            'pay_methods':     [],
        })

    # ── Submit order ─────────────────────────────────────────────────────────
    @http.route(['/uellow/checkout/submit'], type='json', auth='public', website=True, csrf=False)
    def checkout_submit(self, **post):
        order = request.website.sale_get_order()
        if not order or not order.order_line:
            return {'success': False, 'error': 'empty_cart'}

        # A2 — Idempotency guard. If a tx is already pending for this cart,
        # short-circuit and return the previously-issued redirect instead of
        # creating another payment.transaction (which would double-charge).
        sess_key = 'uc_pending_tx_for_order_%d' % order.id
        prev = request.session.get(sess_key)
        if prev and isinstance(prev, dict):
            return prev

        payment_method = (post.get('payment_method') or 'cod').strip()
        is_cod = payment_method.lower() in {'cod', 'cash', 'cash_on_delivery', 'custom'}

        import re as _re
        # Preserve existing delivery note, update payment method
        note = order.note or ''
        if 'Payment:' in note:
            note = _re.sub(r'Payment:.*', 'Payment: ' + payment_method, note)
        else:
            note = (note + chr(10) if note else '') + 'Payment: ' + payment_method
        order.write({'note': note})

        # Ensure delivery line has price. SHIP-GUARD: resolve via the shared
        # resolver so a transient rate failure can't confirm the order with
        # 0 shipping (it falls back to the carrier's fixed price; a genuine
        # free-over 0 is preserved).
        if order.carrier_id:
            try:
                order.sudo().set_delivery_line(
                    order.carrier_id, _uc_ship_price(order.carrier_id, order))
            except Exception as e:
                _logger.warning('rate_shipment: %s', e)

        def _raw():
            request.env.cr.execute(
                'SELECT name, amount_total, currency_id, partner_id FROM sale_order WHERE id = %s',
                (order.id,))
            row = request.env.cr.fetchone()
            return {
                'name':        row[0] if row else 'SO-%d' % order.id,
                'total':       float(row[1]) if row else 0.0,
                'currency_id': row[2] if row else 0,
                'partner_id':  row[3] if row else 0,
            }

        if is_cod:
            # COD: confirm immediately
            # v2.2.40 — flag as cash (field defaults to 'online') so the order
            # tracking page + carrier portal read COD correctly.
            try:
                if 'payment_method_type' in order._fields:
                    order.sudo().payment_method_type = 'cash'
            except Exception:
                pass
            order.action_confirm()
            d = _raw()
            try:
                cur = request.env['sale.order'].sudo().browse(order.id).currency_id.name or ''
            except Exception:
                cur = ''
            _save_uc_order(order, payment_method, request.env)
            request.website.sale_reset()
            return {
                'success': True, 'order_id': order.id,
                'order_name': d['name'], 'amount_total': '%.3f' % d['total'],
                'currency': cur,
                'redirect': '/shop/order/success?order_id=%d' % order.id,
            }

        # Taly installments (4 payments) — MUST route to Taly, NOT UPayments.
        # Previously 'taly' fell through to the UPayments branch below and the
        # safety-net remapped it to KNET, so the customer was sent to KNET.
        if payment_method.lower() == 'taly':
            try:
                # delivery line already set above; amount_total includes it.
                pay_url = order._taly_mobile_charge(_lang())
                if not pay_url:
                    raise Exception('Taly did not return a checkout URL')
                d = _raw()
                _save_uc_order(order, 'taly', request.env)
                # Order stays a draft until the Taly webhook confirms it; just
                # detach it from the session cart and send the customer to Taly.
                request.website.sale_reset()
                return {
                    'success': True, 'redirect': pay_url, 'order_id': order.id,
                    'order_name': d['name'], 'amount_total': '%.3f' % d['total'],
                }
            except Exception as e:
                import traceback
                _logger.error('UELLOW TALY ERROR: %s\n%s', e, traceback.format_exc())
                # Surface Taly's own (bilingual) business message — e.g. the
                # minimum-order rule — so the customer sees the real reason
                # instead of a generic error.
                msg = getattr(e, 'name', None) or str(e) or ''
                if not msg:
                    msg = 'Taly installments unavailable right now — please pick another method'
                return {'success': False, 'error': msg[:300], 'detail': str(e)[:200]}

        # Online payment via UPayments
        # Flow: create tx → call _get_specific_rendering_values (hits UPayments API)
        # → get upay_payment_link_url → redirect customer there
        # After payment, UPayments hits /redirect/success or /redirect/error
        # then Odoo processes notification and redirects to /payment/status
        try:
            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'upayments'), ('state', 'in', ('enabled', 'test'))],
                limit=1)
            if not provider:
                raise Exception('UPayments provider not found or not enabled')

            # Resolve payment method (knet, credit_card, apple_pay, etc.)
            pay_method = None
            try:
                pm_id = int(post.get('payment_method_id') or 0)
                if pm_id > 0:
                    pm = request.env['payment.method'].sudo().browse(pm_id)
                    if pm.exists():
                        pay_method = pm
            except Exception:
                pass
            # Fallback: find by code string
            if not pay_method and payment_method not in ('cod', 'custom'):
                pay_method = request.env['payment.method'].sudo().search(
                    [('code', '=', payment_method), ('active', '=', True)], limit=1)
            # Safety net: UPayments REQUIRES a payment method that maps to a
            # gateway `src` (knet/cc/apple-pay/...). If none resolved, the API
            # rejects the charge with "Payment gateway src is empty" and the
            # customer never gets redirected. Default to a working gateway.
            if not pay_method or pay_method not in provider.payment_method_ids:
                pay_method = (
                    provider.payment_method_ids.filtered(lambda m: m.code == 'knet')
                    or provider.payment_method_ids.filtered(lambda m: m.code == 'credit_card')
                    or provider.payment_method_ids[:1])

            d = _raw()

            tx_vals = {
                'amount':         d['total'],
                'currency_id':    d['currency_id'],
                'partner_id':     d['partner_id'],
                'provider_id':    provider.id,
                'reference':      request.env['payment.transaction'].sudo()._compute_reference(
                                      provider.code, prefix=d['name']),
                'operation':      'online_redirect',
                'sale_order_ids': [(4, order.id)],
                'landing_route':  '/payment/status',
            }
            if pay_method:
                tx_vals['payment_method_id'] = pay_method.id

            tx = request.env['payment.transaction'].sudo().create(tx_vals)
            request.session['__payment_monitored_tx_id__'] = tx.id

            # UPayments flow:
            # 1. _get_processing_values() builds generic + specific values
            # 2. Internally calls _get_specific_rendering_values()
            # 3. UPayments API returns form_url → stored as upay_payment_link_url
            processing_values = tx._get_processing_values()
            _logger.info('UPAY processing_values keys: %s', list(processing_values.keys()))

            # upay_payment_link_url is set by _get_specific_rendering_values inside _get_processing_values
            pay_url = processing_values.get('upay_payment_link_url', '')

            # If not in processing_values, call _get_specific_rendering_values directly
            if not pay_url:
                rendering_values = tx._get_specific_rendering_values(processing_values)
                _logger.info('UPAY rendering_values: %s', rendering_values)
                pay_url = rendering_values.get('upay_payment_link_url', '')

            _logger.info('UPAY final pay_url: %s', pay_url)

            if not pay_url:
                raise Exception('UPayments API did not return payment URL. values=%s' % processing_values)

            # Confirm order and redirect to UPayments payment page
            order.action_confirm()
            _save_uc_order(order, payment_method, request.env)
            request.website.sale_reset()

            response = {
                'success':      True,
                'redirect':     pay_url,
                'order_id':     order.id,
                'order_name':   d['name'],
                'amount_total': '%.3f' % d['total'],
            }
            # A2 — cache response so duplicate submit returns the same redirect.
            request.session[sess_key] = response
            return response

        except Exception as e:
            import traceback
            _logger.error('UELLOW UPAYMENTS ERROR: %s\n%s', e, traceback.format_exc())
            # A1 — DO NOT auto-confirm on payment-gateway failure. That used
            # to mark the order paid even when UPayments threw, causing
            # silent revenue loss. Now we surface the error so the
            # customer can retry / pick another method.
            return {
                'success': False,
                'error':   'Payment gateway error — please retry or pick a different method',
                'detail':  str(e)[:200],
            }



    @http.route(['/uellow/confirm_cod'], type='http', auth='public',
                website=True, sitemap=False, methods=['POST'], csrf=False)
    def confirm_cod(self, **post):
        order = request.website.sale_get_order()
        if not order:
            return _json_resp({'error': 'No active order'})
        try:
            order.with_context(send_email=True).action_confirm()
            _save_uc_order(order, 'cod', request.env)
            request.session.update({'sale_order_id': False})
            return _json_resp({
                'success': True, 'order_id': order.id,
                'redirect': '/shop/order/success?order_id=%d' % order.id,
            })
        except Exception as e:
            return _json_resp({'error': str(e)})

    # ── UPay placeholder ──────────────────────────────────────────────────────
    @http.route(['/uellow/pay'], type='http', auth='public',
                website=True, sitemap=False, methods=['POST'], csrf=False)
    def pay(self, **post):
        return _json_resp({'error': 'use_upayments_flow'})

    # ── Payment methods JSON ──────────────────────────────────────────────────
    @http.route(['/uellow/payment_methods_json'], type='json', auth='public',
                website=True, csrf=False)
    def payment_methods_json(self, **post):
        # IMPORTANT — only expose payment methods that belong to a provider
        # actually usable on THIS storefront. Previously this listed EVERY
        # active payment.method in the DB, including methods owned by the
        # app-only pseudo-website providers (code='custom', website 12–18).
        # A customer could then pick a method whose record is NOT in the
        # storefront UPayments provider, the charge would misroute and the
        # customer ended up on /payment/status ("payment not found") instead
        # of the gateway. We now scope strictly to the website's own
        # enabled providers, so every selectable method maps to a working flow.
        result    = []
        cod_added = False
        _SKIP_SET = {'paypal', 'wire_transfer'}
        _COD_SET  = {'cod', 'cash', 'custom', 'cash_on_delivery'}

        # v2.1.77 — payment derives from the carrier COMPANY (the base): when
        # the order's selected courier doesn't collect cash, hide COD here too
        # (same rule as the app). Default ON when no carrier/company is set.
        cod_allowed = True
        cur_website_id = False
        try:
            cur_website_id = request.website.id
            order = request.website.sale_get_order()
            comp = order.carrier_id.carrier_company_id if order and order.carrier_id else False
            if comp:
                cod_allowed = bool(getattr(comp, 'cod_enabled', True))
        except Exception as e:
            _logger.warning('cod gate: %s', e)

        try:
            # Providers enabled and scoped to this website (global = website_id
            # unset, or explicitly this website). This drops the app-only
            # providers bound to other (pseudo-)websites.
            providers = request.env['payment.provider'].sudo().search(
                ['&', ('state', 'in', ('enabled', 'test')),
                      '|', ('website_id', '=', False),
                           ('website_id', '=', cur_website_id)])
            seen_codes = set()
            for p in providers:
                p_is_cod = (p.code or '').lower() in _COD_SET
                pimg = '/web/image/payment.provider/%d/image_128' % p.id
                for m in (p.payment_method_ids or []):
                    if not m.active:
                        continue
                    code = (getattr(m, 'code', None) or '').strip()
                    if not code:
                        code = 'm%d' % m.id
                    lcode = code.lower()
                    if lcode in _SKIP_SET:
                        continue
                    img = pimg
                    # COD-style provider/method → single Cash-on-Delivery entry
                    if p_is_cod or lcode in _COD_SET:
                        if not cod_added and cod_allowed:
                            cod_added = True
                            result.insert(0, {
                                'id': m.id, 'name': m.name, 'code': 'cod',
                                'image': img, 'is_cod': True, 'is_upay': False,
                            })
                        continue
                    # de-dup by visible code (e.g. one "KNET" even if two
                    # providers expose it) — keep the first (the storefront one)
                    if lcode in seen_codes:
                        continue
                    seen_codes.add(lcode)
                    result.append({
                        'id': m.id, 'name': m.name or '', 'code': code,
                        'image': img, 'is_cod': False, 'is_upay': True,
                    })
        except Exception as e:
            _logger.error('payment_methods_json: %s', e)

        if not result:
            result = [{'id': -1, 'name': 'Cash on Delivery', 'code': 'cod',
                       'image': '', 'is_cod': True, 'is_upay': False}]
        return {'success': True, 'methods': result}

    # ── States ────────────────────────────────────────────────────────────────
    @http.route(['/uellow/states'], type='http', auth='public', website=True, sitemap=False)
    def states(self, country_id=None, **kw):
        result = []
        if country_id:
            try:
                ss = request.env['res.country.state'].sudo().search(
                    [('country_id', '=', int(country_id))], order='name asc')
                result = [{'id': s.id, 'name': s.name} for s in ss]
            except Exception: pass
        return _json_resp(result)

    # ── Order lines (public, for items dialog) ───────────────────────────────
    @http.route(['/uellow/order_lines'], type='http', auth='public', website=True, sitemap=False)
    def order_lines(self, order_id=None, **kw):
        """Return order lines for the items dialog. Only serves lines of the current session order."""
        try:
            current = request.website.sale_get_order()
            if not current or not order_id:
                return _json_resp({'lines': [], 'total': 0})
            oid = int(order_id)
            if current.id != oid:
                return _json_resp({'lines': [], 'total': 0})
            lines = []
            for l in current.sudo().order_line:
                if l.is_delivery:
                    continue
                pid = l.product_id
                lines.append({
                    'name':      pid.name or '',
                    'qty':       int(l.product_uom_qty),
                    'price':     round(l.price_unit, 3),
                    'subtotal':  round(l.price_subtotal, 3),
                    'img_id':    pid.id,
                })
            return _json_resp({
                'lines': lines,
                'total': round(current.sudo().amount_total, 3),
            })
        except Exception as e:
            _logger.warning('order_lines: %s', e)
            return _json_resp({'lines': [], 'total': 0})

    # ── Country by ISO code ───────────────────────────────────────────────────
    @http.route(['/uellow/country_id'], type='http', auth='public', website=True, sitemap=False)
    def country_by_code(self, code=None, **kw):
        if not code:
            return _json_resp({})
        country = request.env['res.country'].sudo().search(
            [('code', '=', code.upper().strip())], limit=1)
        if not country:
            return _json_resp({})
        return _json_resp({'id': country.id, 'name': country.name})

    # ── GeoIP ─────────────────────────────────────────────────────────────────
    @http.route(['/uellow/geoip'], type='http', auth='public', website=True, sitemap=False)
    def geoip_ajax(self, **kw):
        return _json_resp({'success': True, 'geo': _geoip()})

    # ── Reverse geocode ───────────────────────────────────────────────────────
    @http.route(['/uellow/reverse_geocode'], type='http', auth='public', website=True, sitemap=False)
    def reverse_geocode(self, lat=None, lng=None, **kw):
        if not lat or not lng: return _json_resp({})
        try:
            import urllib.request as ur
            url = ('https://nominatim.openstreetmap.org/reverse'
                   '?format=jsonv2&lat=%s&lon=%s&accept-language=ar,en' % (lat, lng))
            req = ur.Request(url, headers={'User-Agent': 'UellowOdoo/3.0'})
            with ur.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            a    = data.get('address', {})
            city = a.get('city') or a.get('town') or a.get('village') or a.get('county') or ''
            gov  = a.get('state') or a.get('region') or ''
            cc   = (a.get('country_code') or '').upper()
            cid  = sid = None
            country = request.env['res.country'].sudo().search([('code', '=', cc)], limit=1)
            if country:
                cid = country.id
                state = request.env['res.country.state'].sudo().search(
                    [('country_id', '=', cid), ('name', 'ilike', gov[:20])], limit=1)
                if state: sid = state.id
            return _json_resp({
                'city': city, 'state': gov, 'country_code': cc,
                'country_id': cid, 'state_id': sid,
                'street': ' '.join(filter(None, [a.get('road'), a.get('house_number')])),
                'full_address': data.get('display_name', ''),
            })
        except Exception as e:
            _logger.warning('revgeo: %s', e)
            return _json_resp({})

    # ── UPayments debug ──────────────────────────────────────────────────────
    @http.route(['/uellow/upay_debug'], type='http', auth='user', website=True, sitemap=False)
    def upay_debug(self, **kw):
        """Debug endpoint — shows UPayments rendering_values. Admin only."""
        # SECURITY: this endpoint runs raw SQL, creates live UPayments charges
        # and deletes payment.transaction rows — restrict to system admins
        # (was auth='user', reachable by any logged-in portal customer).
        if not request.env.user.has_group('base.group_system'):
            return request.not_found()
        import json as _j
        out = {'error': None, 'provider': None, 'rendering_values': None, 'pay_url': None}
        try:
            order = request.website.sale_get_order()
            if not order:
                # Create a dummy test
                out['error'] = 'No active cart — add a product first'
                return Response(_j.dumps(out, indent=2, default=str),
                    headers=[('Content-Type', 'application/json')])

            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'upayments'), ('state', 'in', ('enabled', 'test'))], limit=1)
            if not provider:
                out['error'] = 'UPayments provider not found or not enabled'
                return Response(_j.dumps(out, indent=2, default=str),
                    headers=[('Content-Type', 'application/json')])

            out['provider'] = {'id': provider.id, 'name': provider.name, 'code': provider.code}

            # Create a test transaction (won't confirm order)
            request.env.cr.execute(
                'SELECT name, amount_total, currency_id, partner_id FROM sale_order WHERE id = %s',
                (order.id,))
            row = request.env.cr.fetchone()
            if not row:
                out['error'] = 'Could not read order'
                return Response(_j.dumps(out, indent=2, default=str),
                    headers=[('Content-Type', 'application/json')])

            tx = request.env['payment.transaction'].sudo().create({
                'amount':         float(row[1]),
                'currency_id':    row[2],
                'partner_id':     row[3],
                'provider_id':    provider.id,
                'reference':      'DEBUG-' + str(order.id),
                'operation':      'online_redirect',
                'sale_order_ids': [(4, order.id)],
            })
            base_url = request.website.get_base_url()
            rv = tx._get_specific_rendering_values({
                'amount':     float(row[1]),
                'currency':   request.env['res.currency'].sudo().browse(row[2]),
                'partner_id': row[3],
                'reference':  tx.reference,
                'return_url': base_url + '/shop/order/success',
            })
            out['rendering_values'] = {k: str(v) for k, v in rv.items()}
            # Find URL
            for k, v in rv.items():
                if isinstance(v, str) and v.startswith('http'):
                    out['pay_url'] = {'key': k, 'url': v}
                    break
            # Rollback test tx
            request.env.cr.execute('DELETE FROM payment_transaction WHERE id = %s', (tx.id,))
        except Exception as e:
            import traceback
            out['error'] = traceback.format_exc()
        return Response(_j.dumps(out, indent=2, default=str),
            headers=[('Content-Type', 'application/json')])

    # ── Debug ─────────────────────────────────────────────────────────────────
    @http.route(['/uellow/debug/checkout'], type='http', auth='public',
                website=True, sitemap=False)
    def uc_debug(self, **kw):
        import json as _j
        info = {
            'module': 'uellow_checkout v3', 'controller': 'UellowCheckout',
            'routes': ['/shop/cart', '/shop/checkout', '/shop/payment'],
        }
        return Response(_j.dumps(info, indent=2), status=200,
                        headers=[('Content-Type', 'application/json')])

    # ── Order success ─────────────────────────────────────────────────────────
    @http.route(['/shop/order/success'], type='http', auth='public',
                website=True, sitemap=False)
    def order_success(self, order_id=None, failed=None, **post):
        order = None
        lang  = _lang()
        try:
            if order_id:
                o = request.env['sale.order'].sudo().browse(int(order_id))
                if o.exists(): order = o
        except Exception: pass
        if not order:
            try:
                sid = request.session.get('last_order_id') or request.session.get('sale_order_id')
                if sid:
                    o = request.env['sale.order'].sudo().browse(sid)
                    if o.exists(): order = o
            except Exception: pass
        wa_num = '96597170933'
        try:
            wa_num = request.env['ir.config_parameter'].sudo().get_param(
                'uellow.whatsapp_number', wa_num) or wa_num
        except Exception: pass
        # WhatsApp URL — always generate, with or without order
        if order:
            msg = ('طلبي رقم %s تم تاكيده' % order.name) if lang == 'ar' else ('Order %s confirmed' % order.name)
        else:
            msg = 'مرحبا' if lang == 'ar' else 'Hello'
        import urllib.parse as _urlparse
        wa_url = 'https://wa.me/%s?text=%s' % (wa_num, _urlparse.quote(msg, safe=''))
        return request.render('uellow_checkout.order_success', {
            'order':           order,
            'uc_lang':         lang,
            'currency_symbol': _sym(order) if order else 'KD',
            'whatsapp_url':    wa_url,
            'payment_failed':  (failed == '1'),
        })
