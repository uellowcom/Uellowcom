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


try:
    from odoo.addons.website_sale.controllers.main import WebsiteSale as _WSBase
except ImportError:
    _WSBase = http.Controller


class UellowCheckout(_WSBase):

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
        states = []
        if sel_cid:
            states = request.env['res.country.state'].sudo().search(
                [('country_id', '=', sel_cid)], order='name asc')
        carriers = []
        try:
            all_c = request.env['delivery.carrier'].sudo().search([('website_published', '=', True)])
            for c in all_c:
                price = 0.0
                try:
                    res = c.rate_shipment(order)
                    if isinstance(res, dict) and res.get('success'):
                        price = res.get('price', 0.0) or 0.0
                except Exception:
                    pass
                if price == 0.0:
                    try: price = float(c.fixed_price or 0.0)
                    except Exception: price = 0.0
                carriers.append({'carrier': c, 'price': price})
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
        carrier_id = post.get('carrier_id')
        if carrier_id:
            try:
                c = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
                if c.exists():
                    try:
                        price_unit = 0.0
                        rate = c.rate_shipment(order)
                        if isinstance(rate, dict) and rate.get('success'):
                            price_unit = rate.get('price', 0.0)
                        order.sudo().set_delivery_line(c, price_unit)
                    except Exception as e:
                        _logger.warning('set_delivery_line: %s', e)
                        try:    order._check_carrier_quotation(c)
                        except Exception: order.sudo().write({'carrier_id': c.id})
            except Exception as e:
                _logger.warning('carrier setup: %s', e)
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

        # Ensure delivery line has price
        if order.carrier_id:
            try:
                rate = order.carrier_id.rate_shipment(order)
                if isinstance(rate, dict) and rate.get('success'):
                    order.sudo().set_delivery_line(
                        order.carrier_id, rate.get('price', 0.0))
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
        # Online payment via UPayments:
        # 1. Confirm sale order
        # 2. Create payment.transaction
        # 3. Get form_url from UPayments API via _get_specific_rendering_values
        # 4. Redirect to /notification/info?upay_payment_link_url=<form_url>
        try:
            # Find UPayments provider
            provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'upayments'), ('state', 'in', ('enabled', 'test'))],
                limit=1)
            if not provider:
                raise Exception('UPayments provider not found')

            # Find payment method record
            pay_method = None
            try:
                pm_id = int(post.get('payment_method_id') or 0)
                if pm_id > 0:
                    pay_method = request.env['payment.method'].sudo().browse(pm_id)
                    if not pay_method.exists():
                        pay_method = None
            except Exception:
                pass
            if not pay_method:
                # Fallback: find by code
                pay_method = request.env['payment.method'].sudo().search(
                    [('code', '=', payment_method), ('active', '=', True)], limit=1)

            # Confirm order
            order.action_confirm()
            d = _raw()

            # Create payment transaction
            tx_vals = {
                'amount':             d['total'],
                'currency_id':        d['currency_id'],
                'partner_id':         d['partner_id'],
                'provider_id':        provider.id,
                'reference':          request.env['payment.transaction'].sudo()._compute_reference(
                                          provider.code, prefix=d['name']),
                'operation':          'online_redirect',
                'sale_order_ids':     [(4, order.id)],
                'landing_route':      '/shop/order/success',
            }
            if pay_method:
                tx_vals['payment_method_id'] = pay_method.id
            # Override provider base_url to use website domain
            try:
                base = request.website.get_base_url()
                provider = provider.with_context(base_url=base)
            except Exception:
                pass

            tx = request.env['payment.transaction'].sudo().create(tx_vals)

            # Use Odoo standard flow: _get_processing_values -> _get_specific_rendering_values
            # This is exactly what website_sale does
            rendering_values = tx._get_processing_values()

            form_url     = rendering_values.get('upay_payment_link_url', '')
            redirect_url = '/notification/info'
            if form_url:
                import urllib.parse
                redirect_url = '/notification/info?upay_payment_link_url=' + urllib.parse.quote(form_url, safe='')

            _save_uc_order(order, payment_method, request.env)
            request.website.sale_reset()

            cur_name = ''
            try:
                cur_name = request.env['sale.order'].sudo().browse(order.id).currency_id.name or ''
            except Exception:
                pass

            return {
                'success':      True,
                'order_id':     order.id,
                'order_name':   d['name'],
                'amount_total': '%.3f' % d['total'],
                'currency':     cur_name,
                'redirect':     redirect_url,
            }
        except Exception as e:
            import traceback
            _logger.error('UELLOW UPAYMENTS ERROR: %s\n%s', e, traceback.format_exc())
            # Fallback: confirm without online payment
            try:
                order.action_confirm()
            except Exception:
                pass
            d = _raw()
            _save_uc_order(order, payment_method, request.env)
            request.website.sale_reset()
            return {
                'success': True, 'order_id': order.id,
                'order_name': d['name'], 'amount_total': '%.3f' % d['total'],
                'currency': '', 'redirect': '/shop/order/success?order_id=%d' % order.id,
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
        result    = []
        cod_added = False
        _SKIP_SET = {'paypal', 'wire_transfer'}
        _COD_SET  = {'cod', 'COD', 'custom', 'cash_on_delivery'}
        # Build provider image map
        provider_img = {}
        try:
            for p in request.env['payment.provider'].sudo().search(
                    [('state', 'in', ('enabled', 'test'))]):
                for m in (p.payment_method_ids or []):
                    if m.id not in provider_img:
                        provider_img[m.id] = '/web/image/payment.provider/%d/image_128' % p.id
        except Exception as e:
            _logger.warning('provider_img: %s', e)
        try:
            methods = request.env['payment.method'].sudo().search(
                [('active', '=', True)], order='id asc')
            for m in methods:
                code = (getattr(m, 'code', None) or '').strip()
                if not code: code = 'm%d' % m.id
                if code.lower() in _SKIP_SET: continue
                img = provider_img.get(m.id, '')
                if code in _COD_SET or code.lower() in _COD_SET:
                    if not cod_added:
                        cod_added = True
                        result.insert(0, {
                            'id': m.id, 'name': m.name, 'code': 'cod',
                            'image': img, 'is_cod': True, 'is_upay': False,
                        })
                    continue
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
        wa_url = '#'
        if order:
            msg = ('طلبي رقم %s تم تاكيده' % order.name) if lang == 'ar' else ('Order %s confirmed' % order.name)
            wa_url = 'https://wa.me/%s?text=%s' % (wa_num, msg.replace(' ', '%20'))
        return request.render('uellow_checkout.order_success', {
            'order':           order,
            'uc_lang':         lang,
            'currency_symbol': _sym(order) if order else 'KD',
            'whatsapp_url':    wa_url,
            'payment_failed':  (failed == '1'),
        })
