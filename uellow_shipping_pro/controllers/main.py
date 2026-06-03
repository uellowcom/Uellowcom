"""Public mobile endpoints for the Shipping Pro module.

GET /api/mobile/v2/shipping/cities?country=KW&q=salmi
    Typeahead lookup for the address picker. Returns (id, name_en,
    name_ar, zone_id, zone_tier). `q` is a fuzzy partial match across
    EN, AR, and the aliases column.

GET /api/mobile/v2/shipping/quote?city_id=N&payment=cash|card
    Returns the carriers + total quoted price (delivery_fee +
    cash_surcharge_fixed if applicable) currently available — filters
    out carriers outside their time window.
"""
from datetime import datetime

from odoo import fields, http
from odoo.http import request


def _ok(data):
    return request.make_json_response({'success': True, 'data': data})


def _fail(code, msg, status=400):
    return request.make_json_response(
        {'success': False, 'code': code, 'error': msg}, status=status)


class ShippingProAPI(http.Controller):

    @http.route('/api/mobile/v2/shipping/cities', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    def cities(self, **kw):
        country = (kw.get('country') or 'KW').upper().strip()
        q = (kw.get('q') or '').strip().lower()
        Country = request.env['res.country'].sudo()
        c = Country.search([('code', '=', country)], limit=1)
        if not c:
            return _ok([])
        City = request.env['delivery.city'].sudo()
        dom = [('country_id', '=', c.id), ('active', '=', True)]
        cities = City.search(dom, order='name_en')
        if q:
            norm = lambda s: ''.join(ch for ch in (s or '').lower()
                                     if ch.isalnum())
            tgt = norm(q)
            def matches(city):
                hay = [city.name_en, city.name_ar, city.aliases or '']
                return any(tgt in norm(h) for h in hay if h)
            cities = cities.filtered(matches)
        # v2.1.17 — the app's city picker loads the FULL country list
        # (it filters client-side); typeahead callers can pass limit.
        try:
            limit = min(int(kw.get('limit') or (30 if q else 500)), 500)
        except Exception:
            limit = 30 if q else 500
        out = []
        for city in cities[:limit]:
            zone = city.zone_id
            out.append({
                'id': city.id,
                'name_en': city.name_en or '',
                'name_ar': city.name_ar or '',
                'zone_id': zone.id if zone else 0,
                'zone_name_en': zone.name_en if zone else '',
                'zone_name_ar': zone.name_ar if zone else '',
                'zone_tier': zone.tier if zone else '0',
                'lat': city.lat or 0,
                'lng': city.lng or 0,
            })
        return _ok(out)

    @http.route('/api/mobile/v2/shipping/quote', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    def quote(self, **kw):
        try:
            city_id = int(kw.get('city_id') or 0)
        except Exception:
            city_id = 0
        payment = (kw.get('payment') or 'card').lower()
        City = request.env['delivery.city'].sudo()
        city = City.browse(city_id)
        if not city.exists() or not city.zone_id:
            return _fail('NO_ZONE', 'City has no zone configured', 400)
        zone = city.zone_id
        now = fields.Datetime.now()
        Rule = request.env['carrier.pricing.rule'].sudo()
        rules = Rule.search([('zone_id', '=', zone.id)])
        out = []
        for r in rules:
            cc = r.carrier_company_id
            if not cc:
                continue
            try:
                if not r._within_time_window(now):
                    continue
            except Exception:
                pass
            total = (r.delivery_fee or 0)
            cash = (r.cash_surcharge_fixed or 0) if payment == 'cash' else 0
            total += cash
            out.append({
                'carrier_id': cc.id,
                'carrier_name': cc.name,
                'carrier_kind': getattr(cc, 'carrier_kind', 'third_party'),
                'description_en': getattr(cc, 'description_en', '') or '',
                'description_ar': getattr(cc, 'description_ar', '') or '',
                'rule_id': r.id,
                'zone_name_en': zone.name_en,
                'zone_name_ar': zone.name_ar,
                'delivery_fee': r.delivery_fee or 0,
                'cash_surcharge': cash,
                'total': total,
                'cancel_fee': r.cancel_fee_only or 0,
                'time_window_start': r.time_window_start or 0,
                'time_window_end': r.time_window_end or 0,
            })
        # Sort by total ascending so the cheapest carrier is shown first
        out.sort(key=lambda x: x['total'])
        return _ok(out)
