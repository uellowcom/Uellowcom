# -*- coding: utf-8 -*-
import json
import logging
import urllib.parse
import requests
import jwt
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)
APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_PUBLIC_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

def _get_apple_public_keys():
    try:
        resp = requests.get(APPLE_PUBLIC_KEYS_URL, timeout=10)
        resp.raise_for_status()
        return resp.json().get('keys', [])
    except Exception as e:
        _logger.error("Failed to fetch Apple public keys: %s", e)
        return []

def _verify_apple_identity_token(identity_token, client_id):
    from jwt.algorithms import RSAAlgorithm
    keys = _get_apple_public_keys()
    if not keys:
        raise AccessDenied("Could not fetch Apple public keys.")
    try:
        header = jwt.get_unverified_header(identity_token)
    except Exception:
        raise AccessDenied("Invalid Apple identity token format.")
    kid = header.get('kid')
    matching_key = next((k for k in keys if k.get('kid') == kid), None)
    if not matching_key:
        raise AccessDenied("Apple public key not found.")
    public_key = RSAAlgorithm.from_jwk(json.dumps(matching_key))
    try:
        payload = jwt.decode(identity_token, public_key, algorithms=['RS256'], audience=client_id, issuer=APPLE_ISSUER)
    except Exception as e:
        raise AccessDenied("Token verification failed: %s" % e)
    return payload


class AppleLoginController(http.Controller):

    @http.route('/apple/login/redirect', type='http', auth='public', website=True, csrf=False)
    def apple_login_redirect(self, **kwargs):
        ICP = request.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('apple_login.client_id', '')
        if not client_id:
            return request.redirect('/web/login?apple_error=not_configured')

        redirect_uri = 'https://uellow.com/apple/login/callback'
        params = urllib.parse.urlencode({
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code id_token',
            'scope': 'name email',
            'response_mode': 'form_post',
            'state': 'odoo_apple_login',
        })
        apple_url = APPLE_AUTH_URL + '?' + params
        html = """<!DOCTYPE html>
<html><head>
<meta http-equiv="refresh" content="0;url={url}"/>
<script>window.location.replace("{url}");</script>
</head><body>Redirecting...</body></html>""".format(url=apple_url)
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-cache'),
        ])

    @http.route('/apple/login/callback', type='http', auth='public', website=True, csrf=False, methods=['POST', 'GET'])
    def apple_login_callback(self, **kwargs):
        ICP = request.env['ir.config_parameter'].sudo()
        client_id = ICP.get_param('apple_login.client_id', '')

        error = kwargs.get('error')
        if error:
            return request.redirect('/web/login?apple_error=' + error)

        identity_token = kwargs.get('id_token', '')
        if not identity_token:
            return request.redirect('/web/login?apple_error=no_token')

        user_data = {}
        try:
            user_data = json.loads(kwargs.get('user', '') or '{}')
        except Exception:
            pass

        try:
            payload = _verify_apple_identity_token(identity_token, client_id)
        except AccessDenied as e:
            _logger.warning("Apple token verification failed: %s", e)
            return request.redirect('/web/login?apple_error=token_invalid')

        apple_user_id = payload.get('sub')
        email = payload.get('email', '')
        email_verified = payload.get('email_verified', False)

        if not apple_user_id:
            return request.redirect('/web/login?apple_error=no_sub')

        first_name = user_data.get('name', {}).get('firstName', '') if user_data.get('name') else ''
        last_name = user_data.get('name', {}).get('lastName', '') if user_data.get('name') else ''
        full_name = ('%s %s' % (first_name, last_name)).strip() or email or apple_user_id

        ResUsers = request.env['res.users'].sudo()
        ResPartner = request.env['res.partner'].sudo()

        # Find existing user by apple_user_id
        partner = ResPartner.search([('apple_user_id', '=', apple_user_id)], limit=1)
        user = ResUsers.search([('partner_id', '=', partner.id)], limit=1) if partner else None

        # Find by email
        if not user and email and email_verified:
            user = ResUsers.search([('login', '=', email)], limit=1)
            if user:
                user.partner_id.sudo().write({'apple_user_id': apple_user_id})

        # Create new user
        if not user:
            if not email:
                email = '%s@privaterelay.appleid.com' % apple_user_id
            try:
                new_partner = ResPartner.create({
                    'name': full_name,
                    'email': email,
                    'apple_user_id': apple_user_id,
                })
                user = ResUsers.create({
                    'name': full_name,
                    'login': email,
                    'email': email,
                    'partner_id': new_partner.id,
                    'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                })
                _logger.info("Apple login: Created new portal user %s", email)
            except Exception as e:
                _logger.error("Apple login: Failed to create user: %s", e)
                return request.redirect('/web/login?apple_error=create_failed')

        # Login: set session directly without password
        request.session.uid = user.id
        request.session.login = user.login
        request.session.session_token = user.sudo()._compute_session_token(request.session.sid)
        request.env = request.env(user=user.id)

        _logger.info("Apple login: User %s logged in successfully", user.login)
        return request.redirect('/shop')


class AppleMobileLoginController(http.Controller):

    @http.route('/api/apple/login', type='json', auth='public', csrf=False, cors='*')
    def apple_mobile_login(self, identity_token=None, authorization_code=None,
                           first_name=None, last_name=None, **kwargs):
        """
        Mobile API endpoint for Flutter app Apple Sign-In.

        Flutter sends:
          - identity_token: Apple JWT identity token
          - authorization_code: Apple authorization code
          - first_name: (optional, only on first login)
          - last_name:  (optional, only on first login)

        Returns:
          - uid, session_id, name, email, partner_id  on success
          - error message on failure
        """
        ICP = request.env['ir.config_parameter'].sudo()

        # Support both web client_id and mobile client_id
        mobile_client_id = ICP.get_param('apple_login.mobile_client_id', '')
        web_client_id = ICP.get_param('apple_login.client_id', '')

        if not identity_token:
            return {'error': 'missing_token', 'message': 'identity_token is required'}

        # Try mobile client_id first, fallback to web
        payload = None
        last_error = None
        for client_id in filter(None, [mobile_client_id, web_client_id]):
            try:
                payload = _verify_apple_identity_token(identity_token, client_id)
                break
            except Exception as e:
                last_error = str(e)

        if not payload:
            return {'error': 'token_invalid', 'message': last_error or 'Token verification failed'}

        apple_user_id = payload.get('sub')
        email = payload.get('email', '')
        email_verified = payload.get('email_verified', False)

        if not apple_user_id:
            return {'error': 'no_sub', 'message': 'Apple user ID not found in token'}

        # Build full name
        full_name = ('%s %s' % (first_name or '', last_name or '')).strip()
        if not full_name:
            full_name = email.split('@')[0] if email else apple_user_id

        ResUsers = request.env['res.users'].sudo()
        ResPartner = request.env['res.partner'].sudo()

        # ── Find existing user ───────────────────────────────────────
        partner = ResPartner.search([('apple_user_id', '=', apple_user_id)], limit=1)
        user = ResUsers.search([('partner_id', '=', partner.id)], limit=1) if partner else None

        # Try by email if not found by apple_user_id
        if not user and email and email_verified:
            user = ResUsers.search([('login', '=', email)], limit=1)
            if user:
                user.partner_id.sudo().write({'apple_user_id': apple_user_id})

        # ── Create new user if not found ─────────────────────────────
        if not user:
            if not email:
                email = '%s@privaterelay.appleid.com' % apple_user_id

            allow_signup = ICP.get_param('auth_signup.invitation_scope', 'b2b') == 'b2c'
            if not allow_signup:
                return {'error': 'signup_disabled', 'message': 'New user registration is disabled'}

            try:
                new_partner = ResPartner.create({
                    'name': full_name,
                    'email': email,
                    'apple_user_id': apple_user_id,
                })
                user = ResUsers.create({
                    'name': full_name,
                    'login': email,
                    'email': email,
                    'partner_id': new_partner.id,
                    'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                })
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("Apple mobile login: create user failed: %s", e)
                return {'error': 'create_failed', 'message': str(e)}

        # ── Create Odoo session ──────────────────────────────────────
        request.session.uid = user.id
        request.session.login = user.login
        request.session.db = request.env.cr.dbname
        request.session.context = dict(request.env["res.users"].sudo().context_get())
        request.session.context["uid"] = user.id
        request.session.session_token = user.sudo()._compute_session_token(request.session.sid)

        return {
            'uid': user.id,
            'session_id': request.session.sid,
            'name': user.name,
            'email': user.email or user.login,
            'partner_id': user.partner_id.id,
            'is_new_user': not partner,
        }
