"""Notifications + device registration — /api/mobile/v2/notifications/*"""
from odoo import http, fields
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, current_partner, require_auth, current_session


class MobileNotificationsAPI(http.Controller):

    @http.route('/api/mobile/v2/notifications', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_notifications(self, **kw):
        partner = current_partner()
        prefs = request.env['mobile.notification.preference'].sudo().for_partner(partner)
        Notif = request.env['mobile.notification'].sudo()
        # `partner_id` was never declared on mobile.notification — broadcasts
        # have target_audience='all', specific users go via user_ids.
        items = Notif.search([
            '|', ('user_ids', 'in', [partner.user_ids.id] if partner.user_ids else []),
                 ('target_audience', '=', 'all'),
        ], order='create_date desc', limit=100)
        out = []
        for n in items:
            category = n.category or 'general'
            if not prefs.allows(category):
                continue
            out.append({
                'id': n.id,
                'title': n.name or '',
                'body':  n.body or '',
                'image': '',
                'category': category,
                'data':  {},
                'is_read': False,
                'date':  n.create_date.isoformat() if n.create_date else None,
            })
        # v2.1.62 — merge PERSONAL event notifications (orders, wallet,
        # loyalty, review replies, affiliate…). Their ids are offset by
        # 1e9 so mark-read can route to the right model.
        try:
            import json as _json
            lang = (request.httprequest.headers.get('X-Lang')
                    or '').lower()
            ar = lang.startswith('ar')
            Personal = request.env['mobile.customer.notification'].sudo()
            for n in Personal.search([('partner_id', '=', partner.id)],
                                     order='create_date desc', limit=100):
                out.append({
                    'id': 1000000000 + n.id,
                    'title': (n.title_ar if ar and n.title_ar
                              else n.title) or '',
                    'body': (n.body_ar if ar and n.body_ar
                             else n.body) or '',
                    'image': '',
                    'category': n.category or 'general',
                    'data': _json.loads(n.payload or '{}'),
                    'is_read': bool(n.is_read),
                    'date': n.create_date.isoformat()
                            if n.create_date else None,
                })
            out.sort(key=lambda d: d['date'] or '', reverse=True)
        except Exception:
            pass
        return ok(out)

    @http.route('/api/mobile/v2/notifications/unread-count', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def unread_count(self, **kw):
        """v2.1.63 — badge counter for the account page: number of
        UNREAD personal event notifications (broadcasts excluded — they
        carry no per-user read state)."""
        partner = current_partner()
        n = request.env['mobile.customer.notification'].sudo().search_count(
            [('partner_id', '=', partner.id), ('is_read', '=', False)])
        return ok({'unread': n})

    @http.route('/api/mobile/v2/notifications/read-all', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def read_all(self, **kw):
        """v2.1.63 — clears the account-page badge: marks every personal
        event notification of the customer as read."""
        partner = current_partner()
        recs = request.env['mobile.customer.notification'].sudo().search(
            [('partner_id', '=', partner.id), ('is_read', '=', False)])
        recs.write({'is_read': True})
        request.env.cr.commit()
        return ok({'read': len(recs)})

    @http.route('/api/mobile/v2/notifications/preferences', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def get_preferences(self, **kw):
        partner = current_partner()
        prefs = request.env['mobile.notification.preference'].sudo().for_partner(partner)
        return ok({
            'push_enabled':           prefs.push_enabled,
            'receive_promotions':     prefs.receive_promotions,
            'receive_order_updates':  prefs.receive_order_updates,
            'receive_general':        prefs.receive_general,
            'categories': [
                {'code': 'promotion',
                 'label': {'en': 'Promotions & deals', 'ar': 'العروض والتخفيضات'},
                 'description': {'en': 'Flash sales, discounts, vendor offers',
                                 'ar': 'عروض فلاش، خصومات، عروض البائعين'},
                 'value': prefs.receive_promotions},
                {'code': 'order_update',
                 'label': {'en': 'Order updates', 'ar': 'تحديثات الطلبات'},
                 'description': {'en': 'Confirmed, shipped, out for delivery, delivered',
                                 'ar': 'مؤكد، شُحن، خرج للتوصيل، تم التسليم'},
                 'value': prefs.receive_order_updates},
                {'code': 'general',
                 'label': {'en': 'General info', 'ar': 'معلومات عامة'},
                 'description': {'en': 'App tips, loyalty milestones, policy updates',
                                 'ar': 'نصائح التطبيق، إنجازات الولاء، تحديثات السياسة'},
                 'value': prefs.receive_general},
            ],
        })

    @http.route('/api/mobile/v2/notifications/preferences/save', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def save_preferences(self, **kw):
        p = get_payload()
        partner = current_partner()
        prefs = request.env['mobile.notification.preference'].sudo().for_partner(partner)
        vals = {}
        for key in ('push_enabled', 'receive_promotions',
                    'receive_order_updates', 'receive_general'):
            if key in p:
                vals[key] = bool(p[key])
        if vals:
            prefs.write(vals)
        return ok({'saved': True})

    @http.route('/api/mobile/v2/notifications/<int:notif_id>/read', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def mark_read(self, notif_id, **kw):
        # ids ≥ 1e9 are personal event rows (see list merge above)
        if notif_id >= 1000000000:
            n = request.env['mobile.customer.notification'].sudo()                 .browse(notif_id - 1000000000)
            if n.exists():
                n.is_read = True
                request.env.cr.commit()
            return ok({'read': True})
        n = request.env['mobile.notification'].sudo().browse(notif_id)
        if n.exists() and 'is_read' in n._fields:
            n.is_read = True
        return ok({'read': True})

    @http.route('/api/mobile/v2/notifications/register-device', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def register_device(self, **kw):
        """Update the push token for the current device. Works for
        guests too — the token is attached to the mobile.session row."""
        p = get_payload()
        # Live app language — sent in the payload (preferred) or the
        # X-Lang header every app already attaches. Normalized to
        # 'ar' / 'en' and mirrored onto the partner so push texts follow
        # whatever language the customer is using RIGHT NOW.
        raw_lang = (p.get('lang')
                    or request.httprequest.headers.get('X-Lang') or '')
        push_lang = ('en' if raw_lang.lower().startswith('en')
                     else 'ar') if raw_lang else ''
        sess = current_session()
        if sess:
            sess.sudo().write({
                'push_token': p.get('push_token') or '',
                'fcm_token':  p.get('push_token') or '',
                'app_version': p.get('app_version') or sess.app_version,
                'os_version':  p.get('os_version')  or sess.os_version,
                'device_name': p.get('device_name') or sess.device_name,
                'platform':    p.get('platform')    or sess.platform,
                **({'chosen_lang': raw_lang} if raw_lang else {}),
            })
            # Mirror onto res.partner so push helpers can resolve token
            # directly from partner_id (e.g. when sending order updates).
            try:
                partner = current_partner()
                if partner and p.get('push_token'):
                    vals = {'fcm_token': p['push_token']}
                    if push_lang:
                        vals['push_lang'] = push_lang
                    if (p.get('platform') or '').lower() == 'ios' and p.get('apns_token'):
                        vals['apns_token'] = p['apns_token']
                    partner.sudo().write(vals)
            except Exception:
                pass
            return ok({'session_id': sess.id})
        # No session yet — record a guest session keyed by device_id
        if p.get('device_id'):
            sid = request.env['mobile.session'].sudo().register_session(
                device_id   = p['device_id'],
                platform    = p.get('platform', 'android'),
                app_version = p.get('app_version', ''),
                fcm_token   = p.get('push_token'),
                device_name = p.get('device_name'),
                os_version  = p.get('os_version'),
                ip          = request.httprequest.remote_addr,
            )
            return ok({'session_id': sid})
        return ok({'session_id': None})
