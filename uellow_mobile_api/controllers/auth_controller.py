import json
import logging
import hashlib
import secrets
import datetime

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

TOKEN_TTL_DAYS = 30


def _json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
        headers={'Access-Control-Allow-Origin': '*'},
    )


def _error(msg, code=400):
    return _json_response({'success': False, 'error': msg}, code)


def _require_auth(func):
    """Decorator: validate mobile token."""
    def wrapper(self, *args, **kwargs):
        token = request.httprequest.headers.get('X-Mobile-Token', '')
        if not token:
            return _error('Token required', 401)
        uid = _validate_token(token)
        if not uid:
            return _error('Invalid or expired token', 401)
        request.uid = uid
        return func(self, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


def _validate_token(token):
    """Validate token and return uid."""
    param = request.env['ir.config_parameter'].sudo().search(
        [('key', '=', f'mobile_token_{token}')], limit=1
    )
    if not param:
        return None
    try:
        data    = json.loads(param.value)
        expires = datetime.datetime.fromisoformat(data['expires'])
        if datetime.datetime.now() > expires:
            param.unlink()
            return None
        return data['uid']
    except Exception:
        return None


class MobileAuthController(http.Controller):

    @http.route('/api/v1/auth/login', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({})

        try:
            body  = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _error('Invalid JSON')

        email    = body.get('email', '').strip().lower()
        password = body.get('password', '')

        if not email or not password:
            return _error('Email and password required')

        try:
            uid = request.env['res.users'].sudo()._login(
                request.env.cr.dbname, email, password,
                user_agent_env={'interactive': False}
            )
        except Exception as e:
            _logger.warning('Mobile login failed for %s: %s', email, e)
            return _error('Invalid credentials', 401)

        if not uid:
            return _error('Invalid credentials', 401)

        # Generate token
        token   = secrets.token_urlsafe(32)
        expires = (datetime.datetime.now() + datetime.timedelta(days=TOKEN_TTL_DAYS)).isoformat()

        request.env['ir.config_parameter'].sudo().create({
            'key':   f'mobile_token_{token}',
            'value': json.dumps({'uid': uid, 'expires': expires}),
        })

        user    = request.env['res.users'].sudo().browse(uid)
        partner = user.partner_id

        return _json_response({
            'success': True,
            'token':   token,
            'expires': expires,
            'user': {
                'id':     partner.id,
                'name':   partner.name,
                'email':  partner.email or email,
                'phone':  partner.phone or '',
                'avatar': f'/web/image/res.partner/{partner.id}/image_128',
            },
        })

    @http.route('/api/v1/auth/logout', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def logout(self, **kwargs):
        token = request.httprequest.headers.get('X-Mobile-Token', '')
        if token:
            param = request.env['ir.config_parameter'].sudo().search(
                [('key', '=', f'mobile_token_{token}')], limit=1
            )
            if param:
                param.unlink()
        return _json_response({'success': True})

    @http.route('/api/v1/auth/register', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def register(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({})
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _error('Invalid JSON')

        name     = body.get('name', '').strip()
        email    = body.get('email', '').strip().lower()
        password = body.get('password', '')
        phone    = body.get('phone', '')

        if not name or not email or not password:
            return _error('Name, email, and password required')

        # Check if exists
        existing = request.env['res.users'].sudo().search(
            [('login', '=', email)], limit=1
        )
        if existing:
            return _error('Email already registered', 409)

        try:
            user = request.env['res.users'].sudo().create({
                'name':     name,
                'login':    email,
                'password': password,
                'email':    email,
                'phone':    phone,
                'groups_id': [(4, request.env.ref('base.group_portal').id)],
            })
        except Exception as e:
            _logger.error('Mobile register error: %s', e)
            return _error(str(e))

        # Welcome loyalty points
        LoyaltyAccount = request.env.get('loyalty.account')
        if LoyaltyAccount:
            LoyaltyAccount.sudo().get_or_create(user.partner_id.id)

        return _json_response({
            'success': True,
            'message': 'تم إنشاء الحساب بنجاح',
            'user_id': user.id,
        })
