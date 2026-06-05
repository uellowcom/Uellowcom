# -*- coding: utf-8 -*-
"""
Announcement strips (v2.1.57)
=============================
GET /api/mobile/v2/announcements?screen=home|cart|shop|account|product
→ {strips: [...]} for the current customer/guest + website.
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, get_payload, current_partner, get_website,
)


class MobileAnnouncementsAPI(http.Controller):

    @http.route('/api/mobile/v2/announcements', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_announcements(self, **kw):
        p = get_payload()
        screen = (p.get('screen') or 'home').strip()
        partner = None
        try:
            partner = current_partner()
        except Exception:
            pass
        wid = None
        try:
            wid = get_website().id
        except Exception:
            pass
        strips = request.env['mobile.announcement'].for_screen(
            screen, partner=partner, website_id=wid)
        return ok({'strips': strips})
