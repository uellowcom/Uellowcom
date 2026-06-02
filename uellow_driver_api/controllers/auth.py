# -*- coding: utf-8 -*-
"""Driver auth — /api/driver/v1/auth/*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_session,
    current_driver, bilingual,
)


def _serialize_driver(driver):
    return {
        'id': driver.id,
        'name': driver.name,
        'phone': driver.phone,
        'photo_url': f'/web/image/delivery.driver/{driver.id}/photo?unique={driver.write_date}' if driver.photo else None,
        'vehicle': driver.vehicle_info or '',
        'status': driver.status or 'available',
        'carrier_company': {
            'id': driver.carrier_company_id.id,
            'name': driver.carrier_company_id.name,
        } if driver.carrier_company_id else None,
        'can_send_payment_link': bool(driver.can_send_payment_link),
        'app_lang': driver.app_lang or 'en_US',
    }


class DriverAuthAPI(http.Controller):

    @http.route('/api/driver/v1/auth/login', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def login(self, **kw):
        """Email/phone + password. Matches the portal user attached to a
        delivery.driver record."""
        p = get_payload()
        identifier = (p.get('login') or p.get('phone') or p.get('email') or '').strip()
        password = (p.get('password') or '').strip()
        if not identifier or not password:
            return fail('MISSING_FIELDS', 'login + password required')
        Users = request.env['res.users'].sudo()
        # Try login by exact match first (email or login)
        user = Users.search([('login', '=ilike', identifier)], limit=1)
        if not user:
            # Match by partner phone/mobile
            user = Users.search([
                '|', ('partner_id.phone', '=', identifier),
                     ('partner_id.mobile', '=', identifier),
            ], limit=1)
        if not user:
            return fail('INVALID_CREDENTIALS', 'No driver with that phone/email', 401)
        # Odoo 18: use _check_credentials with a credential dict (the
        # old session.authenticate signature was removed).
        try:
            from odoo.exceptions import AccessDenied
            user.with_user(user.id)._check_credentials(
                {'password': password, 'type': 'password'},
                {'interactive': False})
        except AccessDenied:
            return fail('INVALID_CREDENTIALS', 'Wrong password', 401)
        except Exception as e:
            return fail('INVALID_CREDENTIALS', f'Auth failed: {e}', 401)
        driver = request.env['delivery.driver'].sudo().search(
            [('portal_user_id', '=', user.id)], limit=1)
        if not driver:
            return fail('NOT_A_DRIVER', 'This account is not a driver', 403)
        token, _sess = request.env['driver.session'].sudo().issue(
            driver,
            device_id=p.get('device_id', ''),
            platform=p.get('platform', 'android'),
            app_version=p.get('app_version', ''),
            ip=request.httprequest.remote_addr or '',
            push_token=p.get('push_token', ''),
        )
        return ok({
            'token': token,
            'driver': _serialize_driver(driver),
        })

    @http.route('/api/driver/v1/auth/logout', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def logout(self, **kw):
        sess = current_session()
        if sess:
            sess.revoke()
        return ok({'logged_out': True})

    @http.route('/api/driver/v1/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        return ok({'driver': _serialize_driver(current_driver())})

    @http.route('/api/driver/v1/me/status', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def set_status(self, **kw):
        p = get_payload()
        status = (p.get('status') or '').strip()
        if status not in ('available', 'busy', 'offline'):
            return fail('BAD_STATUS', 'status must be available|busy|offline')
        driver = current_driver()
        driver.sudo().write({'status': status})
        return ok({'status': status})

    @http.route('/api/driver/v1/me/push-token', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def push_token(self, **kw):
        p = get_payload()
        token = (p.get('push_token') or '').strip()
        sess = current_session()
        sess.sudo().write({'push_token': token})
        return ok({'saved': True})

    @http.route('/api/driver/v1/me/preferences', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def preferences(self, **kw):
        p = get_payload()
        driver = current_driver()
        vals = {}
        if p.get('app_lang'):
            vals['app_lang'] = p['app_lang']
        if p.get('notif_prefs') is not None:
            import json
            vals['notif_prefs_json'] = json.dumps(p['notif_prefs'])
        if vals:
            driver.sudo().write(vals)
        return ok({'saved': True, 'app_lang': driver.app_lang})
