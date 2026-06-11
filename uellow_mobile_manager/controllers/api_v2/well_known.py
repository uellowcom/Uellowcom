"""/.well-known/ — Android App Links + iOS Universal Links + smart banner.

These two files have to be served from the apex domain (uellow.com) over
HTTPS for OS-level URL verification. Cloudflare passes them through.
"""
import json

from odoo import http
from odoo.http import request

from ._common import app_setting


_ANDROID_PACKAGE = 'com.uellow.app'
# v2.2.16 — REAL fingerprints (were a generic placeholder + app_setting
# wasn't imported, so this endpoint 500'd and App Links never verified).
# 1) debug keystore — signs ALL direct-download/GitHub APKs (build.gradle
#    keeps debug signing unless UELLOW_SIGN=upload).
# 2) upload keystore — signs the Play AAB. NOTE: Google Play RE-SIGNS with
#    its own app-signing key; add that fingerprint (Play Console → App
#    integrity) to mobile.app.setting.android_fingerprint (comma-separated)
#    once the app is live on Play.
_ANDROID_FINGERPRINTS = [
    'CF:9F:6B:F8:F8:4C:53:94:12:ED:05:8B:97:A5:24:2F:'
    'A4:6E:40:9E:16:F3:EC:29:04:72:82:7C:4E:22:83:44',
    '21:1B:FF:9E:60:F5:AF:77:88:18:58:EC:89:27:27:4A:'
    '0A:A9:88:68:49:43:DB:D6:FC:94:51:FF:5B:C7:0D:A0',
]
_IOS_TEAM_AND_BUNDLE = 'XXXXXXXXXX.com.uellow.app'  # TEAMID.BUNDLEID


class WellKnown(http.Controller):

    @http.route('/.well-known/assetlinks.json', type='http', auth='public',
                methods=['GET'], csrf=False)
    def assetlinks(self):
        setting = None
        try:
            setting = app_setting()
        except Exception:
            pass
        pkg = (setting and getattr(setting, 'android_package', None)) or _ANDROID_PACKAGE
        # DB setting may hold extra fingerprints (comma-separated, e.g. the
        # Play app-signing key) — merged with the built-in debug + upload.
        fps = list(_ANDROID_FINGERPRINTS)
        extra = (setting and getattr(setting, 'android_fingerprint', None)) or ''
        for f in str(extra).split(','):
            f = f.strip().upper()
            if f and f not in fps:
                fps.append(f)
        payload = [
            {
                'relation': ['delegate_permission/common.handle_all_urls'],
                'target': {
                    'namespace': 'android_app',
                    'package_name': pkg,
                    'sha256_cert_fingerprints': fps,
                },
            }
        ]
        return request.make_response(json.dumps(payload, indent=2),
                                      headers=[('Content-Type', 'application/json')])

    @http.route('/.well-known/apple-app-site-association', type='http',
                auth='public', methods=['GET'], csrf=False)
    def aasa(self):
        setting = app_setting()
        appid = (setting and getattr(setting, 'ios_app_id', None)) or _IOS_TEAM_AND_BUNDLE
        # Open EVERY uellow.com link in the app, except the Odoo back-office
        # and the verification files themselves. `components` is used by
        # iOS 13+, `paths` (NOT-first) keeps older iOS working.
        payload = {
            'applinks': {
                'apps': [],
                'details': [{
                    'appID': appid,
                    'components': [
                        {'/': '/web/*',         'exclude': True},
                        {'/': '/web',           'exclude': True},
                        {'/': '/odoo/*',        'exclude': True},
                        {'/': '/.well-known/*', 'exclude': True},
                        # /app = public download landing page → open in the
                        # browser, NOT the app (else it lands on an error page).
                        {'/': '/app',           'exclude': True},
                        {'/': '/app/*',         'exclude': True},
                        {'/': '*'},
                    ],
                    'paths': [
                        'NOT /web/*', 'NOT /web', 'NOT /odoo/*',
                        'NOT /.well-known/*', 'NOT /app', 'NOT /app/*', '*',
                    ],
                }],
            },
            'webcredentials': {
                'apps': [appid],
            },
        }
        return request.make_response(json.dumps(payload),
                                      headers=[('Content-Type', 'application/json')])
