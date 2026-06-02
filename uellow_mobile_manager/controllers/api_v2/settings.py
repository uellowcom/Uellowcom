"""App settings, version check, languages, currencies — /api/mobile/v2/app/*"""
import json
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, img_url


class MobileAppSettingsAPI(http.Controller):

    @http.route('/api/mobile/v2/app/settings', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def settings(self, **kw):
        setting = request.env['mobile.app.setting'].sudo().search([], limit=1)
        if not setting:
            setting = request.env['mobile.app.setting'].sudo().create({})
        website = request.env['website'].sudo().search([], limit=1)
        platform = request.httprequest.args.get('platform', 'android').lower()
        return ok({
            'app_name':       setting.app_name or 'Uellow',
            'logo_url':       img_url('mobile.app.setting', setting.id, 'app_logo',
                                      unique=setting.write_date) if setting.app_logo else None,
            'primary_color':  getattr(setting, 'primary_color', None) or '#F5C320',
            'dark_color':     getattr(setting, 'dark_color', None) or '#412402',
            'support_email':  getattr(setting, 'support_email', '') or '',
            'support_phone':  getattr(setting, 'support_phone', '') or '',
            'whatsapp':       getattr(setting, 'whatsapp_number', '') or '',
            'force_update':   bool(getattr(setting, 'force_update', False)),
            'min_version':    (getattr(setting, 'app_version_ios', '') if platform == 'ios'
                               else getattr(setting, 'app_version_android', '')) or '',
            'maintenance':    bool(getattr(setting, 'maintenance_mode', False)),
            'maintenance_message': getattr(setting, 'maintenance_message', '') or '',
            'social': {
                'facebook':   getattr(setting, 'facebook_url', '') or '',
                'instagram':  getattr(setting, 'instagram_url', '') or '',
                'youtube':    getattr(setting, 'youtube_url', '') or '',
                'tiktok':     getattr(setting, 'tiktok_url', '') or '',
                'twitter':    getattr(setting, 'twitter_url', '') or '',
            },
            'urls': {
                'privacy':   getattr(setting, 'privacy_policy_url', '') or '',
                'terms':     getattr(setting, 'terms_url', '') or '',
                'returns':   getattr(setting, 'returns_url', '') or '',
                'about':     getattr(setting, 'about_us_url', '') or '',
                'contact':   getattr(setting, 'contact_url', '') or '',
                'helpdesk':  getattr(setting, 'helpdesk_url', '') or '',
                'blog':      getattr(setting, 'blog_url', '') or '',
                'play_store':getattr(setting, 'google_play_url', '') or '',
                'app_store': getattr(setting, 'app_store_url', '') or '',
            },
            'features': {
                'wallet':         True,
                'loyalty':        True,
                'reviews':        True,
                'reviewers':      True,
                'smart_fit':      True,
                'beena_chat':     bool(getattr(setting, 'chat_enabled', True)),
                'try_on':         False,
                'social_login':   True,
                'guest_checkout': True,
            },
            'website': {
                'id':              website.id,
                'name':            website.name,
                'domain':          website.domain or '',
                'currency':        website.currency_id.name,
                'currency_symbol': website.currency_id.symbol,
            },
        })

    @http.route('/api/mobile/v2/app/languages', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def languages(self, **kw):
        langs = request.env['res.lang'].sudo().search([('active', '=', True)])
        out = []
        for l in langs:
            # Derive a flag emoji from the locale country code.
            # `en_US` → US → 🇺🇸; `ar_001` (no country) → 🌐 fallback.
            flag = '🌐'
            parts = (l.code or '').split('_')
            if len(parts) > 1 and len(parts[1]) == 2 and parts[1].isalpha():
                cc = parts[1].upper()
                flag = ''.join(chr(127397 + ord(ch)) for ch in cc)
            out.append({
                'code': l.code,
                'name': l.name,
                'iso': l.iso_code or l.code,
                'direction': l.direction or 'ltr',
                'flag': flag,
            })
        return ok(out)

    @http.route('/api/mobile/v2/app/countries', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def countries(self, **kw):
        countries = request.env['res.country'].sudo().search([], order='name asc')
        return ok([{
            'id': c.id, 'name': c.name, 'code': c.code,
            'phone_code': c.phone_code,
            'flag': img_url('res.country', c.id, 'image', unique=c.write_date) if c.image else None,
        } for c in countries])

    @http.route('/api/mobile/v2/app/states', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def states(self, **kw):
        country_id = request.httprequest.args.get('country_id')
        domain = []
        if country_id:
            try:
                domain.append(('country_id', '=', int(country_id)))
            except Exception:
                pass
        states = request.env['res.country.state'].sudo().search(domain, order='name asc')
        return ok([{'id': s.id, 'name': s.name, 'code': s.code, 'country_id': s.country_id.id} for s in states])

    @http.route('/api/mobile/v2/app/version-check', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def version_check(self, **kw):
        """Strict version gate — the app calls this at boot and on
        each foreground. Returns enough info to render either:
          • silent OK
          • "update available, optional"
          • "update REQUIRED, can't proceed" (block all UI)
          • "maintenance mode" (block + show message)
        """
        setting = request.env['mobile.app.setting'].sudo().search([], limit=1)
        client_v = request.httprequest.args.get('version', '0.0.0')
        platform = request.httprequest.args.get('platform', 'android').lower()

        if platform == 'ios':
            min_v   = getattr(setting, 'app_version_ios', '') or ''
            store_url = getattr(setting, 'app_store_url', '') or ''
        else:
            min_v   = getattr(setting, 'app_version_android', '') or ''
            store_url = getattr(setting, 'google_play_url', '') or ''
        latest = getattr(setting, 'latest_version', '') or min_v

        maintenance = bool(getattr(setting, 'maintenance_mode', False))
        maint_msg = {
            'en': getattr(setting, 'maintenance_message_en', None) or getattr(setting, 'maintenance_message', '') or 'We are under maintenance. Please try again later.',
            'ar': getattr(setting, 'maintenance_message_ar', None) or 'نقوم بتحسينات على التطبيق. يُرجى المحاولة لاحقاً.',
        }

        below_min = bool(min_v) and _v_compare(client_v, min_v) < 0
        force = bool(getattr(setting, 'force_update', False)) and below_min
        update_available = bool(latest) and _v_compare(client_v, latest) < 0

        return ok({
            'current_client_version': client_v,
            'min_supported_version': min_v,
            'latest_version': latest,
            'force_update': force,
            'update_available': update_available,
            'maintenance': maintenance,
            'maintenance_message': maint_msg,
            'update_url': store_url,
            'update_title': {
                'en': 'Update required' if force else 'Update available',
                'ar': 'مطلوب التحديث' if force else 'تحديث متاح',
            },
            'update_message': {
                'en': "A new version is required to continue. Please update to keep shopping." if force
                      else "A new version is available with improvements and bug fixes.",
                'ar': 'النسخة الجديدة من التطبيق مطلوبة للمتابعة. يُرجى التحديث للاستمرار في التسوق.' if force
                      else 'نسخة جديدة من التطبيق متاحة مع تحسينات وإصلاحات.',
            },
            'release_notes': {
                'en': getattr(setting, 'release_notes_en', '') or '',
                'ar': getattr(setting, 'release_notes_ar', '') or '',
            },
        })


def _v_compare(a, b):
    """Compare 'x.y.z' style version strings. Returns -1/0/1."""
    def parts(s):
        return tuple(int(p) for p in (s or '0').split('.') if p.isdigit())
    pa, pb = parts(a), parts(b)
    return (pa > pb) - (pa < pb)
