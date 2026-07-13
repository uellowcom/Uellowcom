# -*- coding: utf-8 -*-
"""OAuth callback for dropship providers (AliExpress etc.).

Register  https://<host>/dropship/oauth/callback  as the provider's Callback /
Redirect URL. After the admin approves on the provider site, the browser is
redirected here with ?code=...  We exchange it for tokens and mark the provider
connected, then bounce back to the provider form in the backend.

Note: this runs in a controller context, so `fields` is not imported (use
datetime) and side writes need an explicit commit.
"""
import logging
from datetime import datetime  # noqa: F401 - controller convention (no fields here)

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DropshipOAuthController(http.Controller):

    @http.route('/dropship/oauth/callback', type='http', auth='user', website=False, csrf=False)
    def oauth_callback(self, code=None, state=None, **kw):
        """Receive the OAuth code and exchange it for access/refresh tokens."""
        if not code:
            return self._page("Missing authorization code",
                              "No <code>?code=</code> was returned by the provider.", ok=False)

        Provider = request.env['dropship.provider'].sudo()
        provider = False
        if state and str(state).isdigit():
            provider = Provider.browse(int(state)).exists()
        if not provider:
            # fall back to the (primary) AliExpress provider
            provider = Provider.search([('code', '=', 'aliexpress')],
                                       order='is_primary desc, sequence', limit=1)
        if not provider:
            return self._page("Provider not found",
                              "No AliExpress provider record exists.", ok=False)

        try:
            provider._adapter().exchange_code(code)
            provider.write({'state': 'connected', 'status_message': 'Connected via OAuth callback.'})
            request.env.cr.commit()  # persist token write from the controller
        except Exception as e:  # noqa: BLE001 - show the real error to the admin
            _logger.warning("Dropship OAuth exchange failed: %s", e)
            request.env.cr.rollback()
            return self._page("Token exchange failed", str(e), ok=False)

        # bounce back to the provider form
        action_url = "/odoo/action-uellow_dropship.action_dropship_provider/%s" % provider.id
        return self._page(
            "✅ Connected",
            "AliExpress is now connected. Tokens stored and will auto-refresh.",
            ok=True, link=action_url)

    @staticmethod
    def _page(title, msg, ok=True, link=None):
        color = "#10B981" if ok else "#FF4D4D"
        back = ('<p><a href="%s" style="color:#412402;font-weight:700">'
                '&larr; Back to provider</a></p>' % link) if link else ''
        html = """<!doctype html><html><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Uellow Dropship OAuth</title></head>
        <body style="font-family:Tajawal,Arial,sans-serif;background:#F6F6F6;
        display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0">
        <div style="background:#fff;border-radius:16px;padding:32px 40px;
        box-shadow:0 8px 30px rgba(0,0,0,.08);max-width:460px;text-align:center">
        <h2 style="color:%s;margin:0 0 12px">%s</h2>
        <p style="color:#412402;line-height:1.6">%s</p>%s
        </div></body></html>""" % (color, title, msg, back)
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])
