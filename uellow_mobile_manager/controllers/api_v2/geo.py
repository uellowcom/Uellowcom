"""
Geo + country / website routing — /api/mobile/v2/app/*

geo                GET   ?ip=&country=    → detected + recommended website
countries-list     GET                    → all mappings (for picker)
set-country        POST  country_id       → persist user choice in session
"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail, current_session, get_website


class MobileGeoAPI(http.Controller):

    @http.route('/api/mobile/v2/app/geo', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def geo(self, **kw):
        """Tell the app which website it should be talking to. Order:
        1. Explicit ?country=KW override (e.g. user-set in account)
        2. Real client IP via Cloudflare CF-IPCountry header
        3. Geo lookup via Odoo's res.country._get_country_from_ip
        4. Primary fallback mapping
        5. Hard fallback to the request's current website
        """
        p = get_payload()
        env = request.env
        Mapping = env['mobile.country.website'].sudo()
        sess = current_session()

        # Source 1: explicit override
        chosen_country_code = (p.get('country') or '').upper().strip()
        if not chosen_country_code and sess and sess.country_code:
            chosen_country_code = sess.country_code

        mapping = None
        source = ''
        if chosen_country_code:
            mapping = Mapping.find_for_country_code(chosen_country_code)
            source = 'override' if not (sess and sess.country_code == chosen_country_code) else 'session'

        # Source 2: Cloudflare header (most accurate in prod)
        if not mapping:
            cf_country = (request.httprequest.headers.get('CF-IPCountry') or '').upper()
            if cf_country and cf_country not in ('XX', 'T1'):
                mapping = Mapping.find_for_country_code(cf_country)
                if mapping:
                    source = 'cloudflare'

        # Source 3: Odoo's GeoIP on remote_addr
        if not mapping:
            ip = (p.get('ip') or request.httprequest.remote_addr or '').strip()
            mapping = Mapping.find_for_ip(ip)
            if mapping:
                source = 'geoip'

        # Source 4: primary fallback
        if not mapping:
            mapping = Mapping.search(
                [('is_primary', '=', True), ('active', '=', True)], limit=1)
            if mapping:
                source = 'primary_fallback'

        # Source 5: hard fallback — current request website
        if not mapping:
            ws = get_website()
            return ok({
                'detected_country': None,
                'recommended': {
                    'country': None,
                    'website': {
                        'id': ws.id,
                        'name': ws.name,
                        'domain': ws.domain or '',
                        'api_base': ws.domain or '',
                    },
                    'default_language': None,
                    'currency': ws.currency_id.name,
                    'currency_symbol': ws.currency_id.symbol,
                },
                'source': 'hard_fallback',
                'should_prompt_switch': False,
            })

        # Decide whether the app should prompt "stay or switch?". If
        # user has a manual override AND detected differs, suggest
        # switching but DON'T force.
        detected = source in ('cloudflare', 'geoip')
        manual = bool(sess and sess.country_code)
        should_prompt = (
            detected and manual
            and sess.country_code != mapping.country_id.code
        )

        return ok({
            'detected_country': mapping.country_id.code if detected else None,
            'recommended': mapping.to_dict(),
            'source': source,
            'should_prompt_switch': should_prompt,
            'manual_choice': sess.country_code if (sess and sess.country_code) else None,
        })

    def _detect_country_code(self, kw):
        """Resolve ONLY the user's ISO country code (no primary fallback, so
        the caller can tell 'country has no site' apart from 'is Kuwait')."""
        p = get_payload()
        sess = current_session()
        code = (p.get('country') or kw.get('country') or '').upper().strip()
        if not code and sess and sess.country_code:
            code = (sess.country_code or '').upper()
        if not code:
            cf = (request.httprequest.headers.get('CF-IPCountry') or '').upper()
            if cf and cf not in ('XX', 'T1'):
                code = cf
        if not code:
            try:
                ip = (p.get('ip') or request.httprequest.remote_addr or '').strip()
                c = request.env['res.country'].sudo()._get_country_from_ip(ip)
                code = (c.code if hasattr(c, 'code') else c) or ''
            except Exception:  # noqa: BLE001
                code = ''
        return (code or '').upper()

    @http.route('/api/mobile/v2/app/currencies', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def currencies_list(self, **kw):
        """Currencies the user can switch the app display to (Settings ▸
        Currency). Prices convert live via `fmt_price` once the app sends the
        chosen code in the `X-Currency` header."""
        from ._common import web_currency
        Cur = request.env['res.currency'].sudo()
        # only currencies we actually price a country in (+ USD) — all rated
        codes = ['KWD', 'SAR', 'AED', 'QAR', 'OMR', 'EGP', 'USD']
        current = web_currency()
        out = []
        for code in codes:
            c = Cur.with_context(active_test=False).search(
                [('name', '=', code)], limit=1)
            if not c:
                continue
            out.append({
                'code': c.name,
                'symbol': c.symbol or c.name,
                'name': c.full_name or c.name,
                'digits': c.decimal_places,
                'selected': c.id == current.id,
            })
        return ok({'currencies': out, 'current': current.name})

    @http.route('/api/mobile/v2/app/countries-list', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def countries_list(self, **kw):
        """Full list for the country picker on app launch / in settings.

        Reordered for a friendlier first-open: the user's own country floats to
        the top IF it has a Uellow website; otherwise China (Uellow World) is
        shown first, since anyone with no local site can still buy from China.
        """
        Mapping = request.env['mobile.country.website'].sudo()
        mappings = Mapping.search([('active', '=', True)])
        ordered = list(mappings)

        code = self._detect_country_code(kw)
        # DIRECT search (no primary fallback) → empty when the country has no site
        site = Mapping.search([('country_id.code', '=', code),
                               ('active', '=', True)], limit=1) if code else Mapping.browse()
        first = site or Mapping.search([('country_id.code', '=', 'CN'),
                                        ('active', '=', True)], limit=1) \
            or Mapping.search([('is_primary', '=', True), ('active', '=', True)], limit=1)
        if first and first in ordered:
            ordered.remove(first)
            ordered.insert(0, first)

        return ok([m.to_dict() for m in ordered])

    @http.route('/api/mobile/v2/app/set-country', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def set_country(self, **kw):
        """Persist the user's manual country choice on their session
        so we don't keep prompting them."""
        p = get_payload()
        code = (p.get('country') or '').upper().strip()
        lang = (p.get('lang') or '').strip()
        # v2.2.00 — server-side availability gate: a gated country can't
        # be selected even if an old client tries.
        if code:
            m0 = request.env['mobile.country.website'].sudo() \
                .find_for_country_code(code)
            if m0 and not getattr(m0, 'app_available', True):
                d = m0.to_dict()
                return fail('COUNTRY_UNAVAILABLE',
                            (d['unavailable_message'].get('ar')
                             or d['unavailable_message'].get('en')
                             or 'Coming soon'), 400)
        sess = current_session()
        if not sess:
            # Guest with no session yet — bootstrap one from device_id
            device_id = p.get('device_id') or ''
            if not device_id:
                return fail('NO_SESSION',
                            'Send device_id so we can create a guest session', 400)
            sid = request.env['mobile.session'].sudo().register_session(
                device_id=device_id, platform=p.get('platform', 'android'),
                app_version=p.get('app_version', ''),
                ip=request.httprequest.remote_addr,
            )
            sess = request.env['mobile.session'].sudo().browse(sid)
        sess.sudo().write({
            'country_code': code or False,
            'chosen_lang': lang or False,
        })
        mapping = request.env['mobile.country.website'].sudo().find_for_country_code(code)
        return ok({
            'saved': True,
            'recommended': mapping.to_dict() if mapping else None,
        })
