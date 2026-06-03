"""/.well-known/ — Android App Links + iOS Universal Links + smart banner.

These two files have to be served from the apex domain (uellow.com) over
HTTPS for OS-level URL verification. Cloudflare passes them through.
"""
import json

from odoo import http
from odoo.http import request


# Replace with the real SHA-256 fingerprint of the production signing key
# once the APK has been signed for Play Store. The fingerprint is taken
# from `keytool -list -v -keystore release.keystore`. Until then, use the
# debug build's fingerprint so internal testing works.
_ANDROID_PACKAGE = 'com.uellow.app'
_ANDROID_FINGERPRINT = (
    # Placeholder — the build hook reads this from `mobile.app.setting`
    # if the value below is overridden in settings.
    'FA:C6:17:45:DC:09:03:78:6F:B9:ED:E6:2A:96:2B:39:9F:73:48:F0:BB:'
    '6F:89:9B:83:32:66:75:91:03:3B:9C'
)
_IOS_TEAM_AND_BUNDLE = 'XXXXXXXXXX.com.uellow.app'  # TEAMID.BUNDLEID


class WellKnown(http.Controller):

    @http.route('/.well-known/assetlinks.json', type='http', auth='public',
                methods=['GET'], csrf=False)
    def assetlinks(self):
        setting = app_setting()
        pkg = (setting and getattr(setting, 'android_package', None)) or _ANDROID_PACKAGE
        fp = (setting and getattr(setting, 'android_fingerprint', None)) or _ANDROID_FINGERPRINT
        payload = [
            {
                'relation': ['delegate_permission/common.handle_all_urls'],
                'target': {
                    'namespace': 'android_app',
                    'package_name': pkg,
                    'sha256_cert_fingerprints': [fp],
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
        payload = {
            'applinks': {
                'apps': [],
                'details': [{
                    'appID': appid,
                    'paths': [
                        '/shop/*', '/product/*', '/category/*',
                        '/my/orders/*', '/my/orders', '/coupons*',
                        '/brand/*', '/promo/*',
                    ],
                }],
            },
            'webcredentials': {
                'apps': [appid],
            },
        }
        return request.make_response(json.dumps(payload),
                                      headers=[('Content-Type', 'application/json')])
