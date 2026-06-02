# -*- coding: utf-8 -*-
"""Vendor auth — /api/vendor/v1/auth/*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, current_session, img_url,
)


def _serialize_vendor(v):
    return {
        'id': v.id,
        'store_name': {
            'en': v.store_name_en or '',
            'ar': v.store_name_ar or v.store_name_en or '',
        },
        'tagline': {
            'en': v.store_tagline_en or '',
            'ar': v.store_tagline_ar or v.store_tagline_en or '',
        },
        'slug': v.store_slug or '',
        'state': v.state or 'pending',
        'tier': v.tier or 'bronze',
        'brand_color': v.brand_color or '#F5C320',
        'logo_url': img_url('uellow.vendor', v.id, 'logo_image',
                            unique=v.write_date) if v.logo_image else None,
        'banner_url': img_url('uellow.vendor', v.id, 'banner_image',
                              unique=v.write_date) if v.banner_image else None,
        'currency': v.currency_id.name if v.currency_id else 'KWD',
        'currency_symbol': v.currency_id.symbol if v.currency_id else 'KD',
        'country': v.country_id.code if v.country_id else '',
        'business_name': v.business_name or '',
        'contact_phone': v.contact_phone or '',
        'contact_email': v.contact_email or v.partner_id.email or '',
        'bank_iban': v.bank_iban or '',
        'bank_name': v.bank_name or '',
        'wallet_balance': float(v.wallet_balance or 0),
        'avg_rating': round(float(v.avg_rating or 0), 2),
        'follower_count': int(v.follower_count or 0),
        'order_count': int(v.order_count or 0),
        'total_sales': float(v.total_sales or 0),
    }


class VendorAuthAPI(http.Controller):

    @http.route('/api/vendor/v1/auth/login', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def login(self, **kw):
        p = get_payload()
        identifier = (p.get('login') or p.get('email') or p.get('phone') or '').strip()
        password = (p.get('password') or '').strip()
        if not identifier or not password:
            return fail('MISSING_FIELDS', 'login + password required')
        Users = request.env['res.users'].sudo()
        user = Users.search([('login', '=ilike', identifier)], limit=1)
        if not user:
            user = Users.search([
                '|', ('partner_id.phone', '=', identifier),
                     ('partner_id.mobile', '=', identifier),
            ], limit=1)
        if not user:
            return fail('INVALID_CREDENTIALS', 'No vendor with that login', 401)
        # Odoo 18 _check_credentials with credential dict.
        try:
            from odoo.exceptions import AccessDenied
            user.with_user(user.id)._check_credentials(
                {'password': password, 'type': 'password'},
                {'interactive': False})
        except AccessDenied:
            return fail('INVALID_CREDENTIALS', 'Wrong password', 401)
        except Exception as e:
            return fail('INVALID_CREDENTIALS', f'Auth failed: {e}', 401)
        vendor = request.env['uellow.vendor'].sudo().search(
            [('user_id', '=', user.id)], limit=1)
        if not vendor:
            return fail('NOT_A_VENDOR', 'This account is not a vendor', 403)
        token, _sess = request.env['vendor.session'].sudo().issue(
            vendor,
            device_id=p.get('device_id', ''),
            platform=p.get('platform', 'android'),
            app_version=p.get('app_version', ''),
            ip=request.httprequest.remote_addr or '',
            push_token=p.get('push_token', ''),
        )
        return ok({'token': token, 'vendor': _serialize_vendor(vendor)})

    @http.route('/api/vendor/v1/auth/logout', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def logout(self, **kw):
        sess = current_session()
        if sess:
            sess.revoke()
        return ok({'logged_out': True})

    @http.route('/api/vendor/v1/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        return ok({'vendor': _serialize_vendor(current_vendor())})

    @http.route('/api/vendor/v1/me/push-token', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def push_token(self, **kw):
        p = get_payload()
        sess = current_session()
        sess.sudo().write({'push_token': (p.get('push_token') or '').strip()})
        return ok({'saved': True})
