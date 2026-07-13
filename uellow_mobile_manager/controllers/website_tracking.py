# -*- coding: utf-8 -*-
"""Website visitor journey ingest — mirrors the app's /api/mobile/v2/track
for the storefront. A small frontend script (uellow_theme_common) beacons
page views + time-on-page here, landing in the SAME uellow.customer.activity
model so the admin 'Customer activity' console shows web + app together."""
import json

from odoo import http
from odoo.http import request


class WebsiteActivityController(http.Controller):

    @http.route('/website/track', type='http', auth='public', csrf=False,
                methods=['POST'], website=True, sitemap=False)
    def website_track(self, **kw):
        try:
            raw = request.httprequest.get_data()
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {}
        events = data.get('events')
        if events is None and data.get('event'):
            events = [data]
        if not isinstance(events, list) or not events:
            return request.make_json_response({'stored': 0})
        n = 0
        try:
            user = request.env.user
            partner = user.partner_id if not user._is_public() else False
            website = getattr(request, 'website', None)
            sid = request.session.sid
            # group this browser session's events under its session id
            for e in events:
                if isinstance(e, dict):
                    e.setdefault('session_token', 'web-%s' % (sid or '')[:24])
            n = request.env['uellow.customer.activity'].sudo().record_batch(
                events, partner=partner, platform='web', website=website)
            request.env.cr.commit()
        except Exception:
            n = 0
        return request.make_json_response({'stored': n})
