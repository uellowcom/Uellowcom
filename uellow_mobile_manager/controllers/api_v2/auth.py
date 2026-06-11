"""
Auth endpoints — /api/mobile/v2/auth/*
======================================

login           POST  email + password           → token + user
register        POST  email + password + name    → token + user
otp/request     POST  phone                      → sent: bool
otp/verify      POST  phone + code               → token + user
social/google   POST  id_token                   → token + user
social/apple    POST  identity_token + name      → token + user
forgot          POST  email                      → sent: bool
logout          POST  (auth)                     → ok
me              GET   (auth)                     → user
"""
import logging
import re

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, issue_token,
    current_partner, current_session, require_auth, img_url, base_url, get_website,
)

_logger = logging.getLogger(__name__)


def _serialize_user(partner):
    if not partner:
        return None
    user = partner.user_ids[:1]
    return {
        'id':       partner.id,
        'user_id':  user.id if user else None,
        'name':     partner.name or '',
        'email':    partner.email or '',
        'phone':    partner.phone or partner.mobile or '',
        'avatar':   img_url('res.partner', partner.id, 'image_256',
                            unique=partner.write_date),
        'is_company': bool(partner.is_company),
        'country':  partner.country_id.code if partner.country_id else None,
        'lang':     partner.lang or 'en_US',
        'wallet_balance': float(getattr(partner, 'wallet_balance', 0) or 0),
        'loyalty_points': _loyalty_points(partner),
        'addresses_count': len(partner.child_ids.filtered(lambda c: c.type in ('delivery', 'invoice'))),
    }


def _loyalty_points(partner):
    """Read from loyalty.card — the LIVE points system."""
    if not partner:
        return 0
    try:
        cards = request.env['loyalty.card'].sudo().search([
            ('partner_id', '=', partner.id),
        ])
        return int(sum(cards.mapped('points')))
    except Exception:
        return 0


class MobileAuthAPI(http.Controller):

    # ─── Login (email + password) ─────────────────────────────────────
    @http.route('/api/mobile/v2/auth/login', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def login(self, **kw):
        p = get_payload()
        email = (p.get('email') or p.get('login') or p.get('username') or '').strip().lower()
        password = p.get('password') or ''
        if not email or not password:
            return fail('MISSING_FIELDS', 'Email and password are required')

        # Odoo 18 changed `session.authenticate` to take a credential
        # dict and return a dict. Older signature still works on 17 but
        # not in 18 — explicitly pass the dict form for forward compat.
        uid = None
        try:
            from odoo.exceptions import AccessDenied
            Users = request.env['res.users'].sudo()
            # Match by login, OR by partner phone/mobile if the user
            # typed their phone number instead of their email.
            user = Users.search([('login', '=', email)], limit=1)
            if not user and email:
                # Strip non-digit characters for phone matching
                digits = ''.join(ch for ch in email if ch.isdigit())
                if len(digits) >= 6:
                    Partner = request.env['res.partner'].sudo()
                    partners = Partner.search([
                        '|', ('phone', 'ilike', digits),
                             ('mobile', 'ilike', digits),
                    ], limit=5)
                    for pp in partners:
                        u = Users.search([('partner_id', '=', pp.id)], limit=1)
                        if u:
                            user = u
                            break
            if user:
                try:
                    # _check_credentials raises AccessDenied on bad pw
                    user.with_user(user.id)._check_credentials(
                        {'password': password, 'type': 'password'},
                        {'interactive': False},
                    )
                    uid = user.id
                except (AccessDenied, TypeError, ValueError):
                    # TypeError = older Odoo with different signature
                    try:
                        user.with_user(user.id)._check_credentials(
                            password, {'interactive': False})
                        uid = user.id
                    except AccessDenied:
                        uid = None
        except Exception as e:
            _logger.warning('Login failed for %s: %s', email, e)
            return fail('INVALID_CREDENTIALS', 'Invalid email or password', 401)

        if not uid:
            return fail('INVALID_CREDENTIALS', 'Invalid email or password', 401)

        user = request.env['res.users'].sudo().browse(uid)
        partner = user.partner_id
        token = issue_token(
            partner_id=partner.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({
            'token': token,
            'user': _serialize_user(partner),
        })

    # ─── Register ─────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/register', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def register(self, **kw):
        p = get_payload()
        email = (p.get('email') or '').strip().lower()
        password = p.get('password') or ''
        name = (p.get('name') or '').strip()
        phone = (p.get('phone') or '').strip()

        if not email or not password or not name:
            return fail('MISSING_FIELDS', 'Name, email and password are required')
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return fail('INVALID_EMAIL', 'Invalid email format')
        if len(password) < 6:
            return fail('WEAK_PASSWORD', 'Password must be at least 6 characters')

        Users = request.env['res.users'].sudo()
        if Users.search_count([('login', '=', email)]):
            return fail('EMAIL_TAKEN', 'Email already registered', 409)

        website = get_website()
        try:
            new_user = Users.with_context(no_reset_password=True).create({
                'name':  name,
                'login': email,
                'email': email,
                'phone': phone,
                'password': password,
                'groups_id': [(6, 0, [
                    request.env.ref('base.group_portal').id,
                ])],
                'website_id': website.id,
            })
        except Exception as e:
            return fail('REGISTER_FAILED', str(e), 400)

        token = issue_token(
            partner_id=new_user.partner_id.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({
            'token': token,
            'user':  _serialize_user(new_user.partner_id),
        })

    # ─── OTP via SMS (Firebase phone auth — verify on Odoo side) ──────
    @http.route('/api/mobile/v2/auth/otp/request', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_request(self, **kw):
        """We rely on Firebase Phone Auth for actually sending the SMS.
        Flutter calls Firebase, gets the ID token, and posts it to
        /otp/verify. This endpoint exists for symmetry / future fallback
        and returns a hint to the app."""
        p = get_payload()
        phone = (p.get('phone') or '').strip()
        if not phone:
            return fail('MISSING_PHONE', 'Phone number required')
        return ok({'provider': 'firebase', 'sent': True})

    # ─── OTP verify (after Firebase confirms the phone) ───────────────
    @http.route('/api/mobile/v2/auth/otp/verify', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_verify(self, **kw):
        p = get_payload()
        phone = (p.get('phone') or '').strip()
        firebase_uid = (p.get('firebase_uid') or '').strip()
        if not phone:
            return fail('MISSING_PHONE', 'Phone number required')

        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = Partner.search([('mobile', '=', phone)], limit=1)
        if not partner:
            # Auto-create a minimal portal user keyed by phone.
            login = f'+otp-{phone.replace("+", "").replace(" ", "")}@uellow.app'
            Users = request.env['res.users'].sudo()
            new_user = Users.with_context(no_reset_password=True).create({
                'name':  p.get('name') or phone,
                'login': login,
                'phone': phone,
                'mobile': phone,
                'password': firebase_uid or 'firebase-otp',
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
            })
            partner = new_user.partner_id
        token = issue_token(
            partner_id=partner.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({'token': token, 'user': _serialize_user(partner)})

    # ─── Social: Google ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/social/google', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def social_google(self, **kw):
        return self._social_passthrough(provider='google')

    # ─── Social: Apple ────────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/social/apple', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def social_apple(self, **kw):
        return self._social_passthrough(provider='apple')

    # ─── Social: Facebook ─────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/social/facebook', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def social_facebook(self, **kw):
        return self._social_passthrough(provider='facebook')

    def _social_passthrough(self, provider):
        """v2.1.16 — server-side verification is REQUIRED. The old
        trust-the-client email flow let anyone mint a token for any
        address. Google: verify `id_token` against Google tokeninfo
        (+ optional audience check via uellow_mobile.google_client_id).
        Apple/Facebook: pending their platform credentials."""
        p = get_payload()
        email = ''
        name = (p.get('name') or '').strip()
        uid = (p.get('provider_user_id') or p.get('uid') or '').strip()

        if provider == 'google':
            id_token = (p.get('id_token') or '').strip()
            if not id_token:
                return fail('MISSING_TOKEN', 'Google id_token required', 400)
            try:
                import requests as _rq
                r = _rq.get('https://oauth2.googleapis.com/tokeninfo',
                            params={'id_token': id_token}, timeout=10)
                info = r.json() if r.status_code == 200 else {}
            except Exception:
                info = {}
            if not info or info.get('email_verified') not in ('true', True):
                return fail('INVALID_TOKEN', 'Google token rejected', 401)
            ICP = request.env['ir.config_parameter'].sudo()
            allowed = (ICP.get_param('uellow_mobile.google_client_id') or '').strip()
            if allowed and info.get('aud') not in [
                    a.strip() for a in allowed.split(',') if a.strip()]:
                return fail('INVALID_AUDIENCE', 'Google client mismatch', 401)
            email = (info.get('email') or '').strip().lower()
            name = name or (info.get('name') or '')
            uid = info.get('sub') or uid
        elif provider == 'apple':
            # v2.1.89 — verify the Apple identity token (JWT) against Apple's
            # public keys + audience = our client id (apple_login.client_id).
            id_token = (p.get('id_token') or p.get('identity_token') or '').strip()
            if not id_token:
                return fail('MISSING_TOKEN', 'Apple identity token required', 400)
            try:
                import jwt
                from jwt import PyJWKClient
                ICP = request.env['ir.config_parameter'].sudo()
                client_id = (ICP.get_param('apple_login.client_id')
                             or 'com.uellow.app').strip()
                # v2.1.95 — Android signs in through the web flow whose
                # audience is the SERVICES id; iOS native uses the bundle
                # id. Accept every configured Apple client id.
                Cfg = request.env.get('apple.login.config')
                audiences = {client_id, 'com.uellow.app', 'com.uellow.signin'}
                if Cfg is not None:
                    audiences |= set(Cfg.sudo().search([]).mapped('client_id'))
                jwks = PyJWKClient('https://appleid.apple.com/auth/keys')
                key = jwks.get_signing_key_from_jwt(id_token).key
                info = jwt.decode(id_token, key, algorithms=['RS256'],
                                  audience=list(a for a in audiences if a),
                                  issuer='https://appleid.apple.com')
            except Exception as e:
                return fail('INVALID_TOKEN', 'Apple token rejected: %s' % e, 401)
            uid = info.get('sub') or uid
            # Apple only returns the email on the FIRST sign-in; afterwards use
            # the app-provided email, else a stable per-user synthetic login.
            email = (info.get('email') or p.get('email') or '').strip().lower()
            if not email and uid:
                email = 'apple-%s@privaterelay.uellow.app' % uid
            name = name or (p.get('name') or '')
        else:
            return fail('PROVIDER_NOT_READY',
                        f'{provider} sign-in is not configured yet', 400)

        if not email:
            return fail('MISSING_EMAIL', f'{provider} email required')

        Users = request.env['res.users'].sudo()
        user = Users.search([('login', '=', email)], limit=1)
        if not user:
            new_user = Users.with_context(no_reset_password=True).create({
                'name': name or email.split('@')[0],
                'login': email,
                'email': email,
                'password': uid or f'social-{provider}',
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
            })
            user = new_user
            # v2.2.03 — partner country follows the WEBSITE the customer
            # signed up from (geo-IP used to tag e.g. Egypt, dragging an
            # EGP pricelist onto Kuwait carts + a wrong account flag).
            try:
                m = request.env['mobile.country.website'].sudo().search(
                    [('website_id', '=', get_website().id),
                     ('active', '=', True)], limit=1)
                if m:
                    user.partner_id.sudo().country_id = m.country_id.id
            except Exception:
                pass
        token = issue_token(
            partner_id=user.partner_id.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({'token': token, 'user': _serialize_user(user.partner_id)})

    # ─── Firebase Phone Auth (OTP via Firebase — no SMS gateway needed) ──
    @http.route('/api/mobile/v2/auth/firebase', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def auth_firebase(self, **kw):
        """Verify a Firebase ID token (the device did the phone/SMS or social
        sign-in via Firebase Auth) and log the customer in / create them.
        Firebase delivers the OTP SMS itself, so no SMS provider is required.

        Body: id_token (required), optional phone, name, device_*.
        """
        import jwt
        import requests as _rq
        from cryptography.x509 import load_pem_x509_certificate
        p = get_payload()
        id_token = (p.get('id_token') or p.get('token') or '').strip()
        if not id_token:
            return fail('MISSING_TOKEN', 'Firebase token required', 400)
        ICP = request.env['ir.config_parameter'].sudo()
        project = (ICP.get_param('mail_mobile_firebase_project_id')
                   or 'uellow-app').strip()
        try:
            kid = jwt.get_unverified_header(id_token).get('kid')
            certs = _rq.get(
                'https://www.googleapis.com/robot/v1/metadata/x509/'
                'securetoken@system.gserviceaccount.com', timeout=10).json()
            pem = certs.get(kid)
            if not pem:
                raise Exception('unknown signing key')
            pub = load_pem_x509_certificate(pem.encode()).public_key()
            info = jwt.decode(
                id_token, pub, algorithms=['RS256'], audience=project,
                issuer='https://securetoken.google.com/%s' % project)
        except Exception as e:
            return fail('INVALID_TOKEN', 'Firebase token rejected: %s' % e, 401)

        phone = (info.get('phone_number') or p.get('phone') or '').strip()
        email = (info.get('email') or '').strip().lower()
        name = (p.get('name') or info.get('name') or '').strip()
        digits = ''.join(ch for ch in phone if ch.isdigit())
        fb_uid = info.get('user_id') or info.get('sub') or ''

        Partner = request.env['res.partner'].sudo()
        Users = request.env['res.users'].sudo()
        user = None

        # 1) match an EXISTING customer by phone (keep their orders + loyalty)
        if len(digits) >= 8:
            pr = Partner.search(['|', ('phone', 'like', digits[-8:]),
                                 ('mobile', 'like', digits[-8:])], limit=1)
            if pr:
                user = pr.user_ids[:1]
                if not user:
                    login = (pr.email or '').strip().lower() \
                        or ('phone-%s@uellow.app' % digits)
                    existing = Users.search([('login', '=', login)], limit=1)
                    user = existing or Users.with_context(
                        no_reset_password=True).create({
                            'name': pr.name or name or login,
                            'login': login,
                            'partner_id': pr.id,
                            'password': 'fb-%s' % (fb_uid or digits),
                            'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                        })
        # 2) else match by email
        if not user and email:
            user = Users.search([('login', '=', email)], limit=1)
        # 3) else create a fresh customer
        if not user:
            login = email or ('phone-%s@uellow.app' % (digits or fb_uid or 'x'))
            user = Users.with_context(no_reset_password=True).create({
                'name': name or phone or login,
                'login': login,
                'email': email or False,
                'password': 'fb-%s' % (fb_uid or digits or login),
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
            })
            try:
                m = request.env['mobile.country.website'].sudo().search(
                    [('website_id', '=', get_website().id), ('active', '=', True)],
                    limit=1)
                if m:
                    user.partner_id.sudo().country_id = m.country_id.id
            except Exception:
                pass

        # store the phone on the partner if it's missing
        if phone and user and not (user.partner_id.phone or user.partner_id.mobile):
            user.partner_id.sudo().mobile = phone

        token = issue_token(
            partner_id=user.partner_id.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({'token': token, 'user': _serialize_user(user.partner_id)})

    # ─── Email OTP (works today — no SMS provider needed) ─────────────
    @http.route('/api/mobile/v2/auth/otp/email/request', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_email_request(self, **kw):
        """Send a 6-digit one-time code to the given email (or to the
        email of the account matching the given phone)."""
        import random
        p = get_payload()
        target = (p.get('email') or p.get('email_or_phone') or '').strip()
        if not target:
            return fail('MISSING_TARGET', 'Email required', 400)
        email_to = target.lower()
        if '@' not in email_to:
            # Treat as phone — find the account's email
            Partner = request.env['res.partner'].sudo()
            digits = ''.join(ch for ch in email_to if ch.isdigit())
            pr = Partner.search(['|', ('phone', 'like', digits[-8:]),
                                 ('mobile', 'like', digits[-8:])], limit=1) \
                if len(digits) >= 8 else Partner.browse([])
            if not pr or not pr.email:
                return fail('NO_ACCOUNT',
                            'No account with this phone — use your email', 404)
            email_to = pr.email.lower()
        code = '%06d' % random.randint(0, 999999)
        request.env['mobile.otp.code'].sudo().issue(email_to, code)
        try:
            request.env['mail.mail'].sudo().create({
                'subject': 'Uellow sign-in code: %s' % code,
                'email_to': email_to,
                'body_html': (
                    '<div style="font-family:sans-serif">'
                    '<h2 style="color:#412402">%s</h2>'
                    '<p>Your Uellow sign-in code / رمز الدخول الخاص بك:</p>'
                    '<p style="font-size:30px;font-weight:bold;'
                    'letter-spacing:6px;color:#412402">%s</p>'
                    '<p>Valid for 10 minutes. صالح لمدة ١٠ دقائق.</p>'
                    '</div>') % ('Uellow', code),
            }).send()
        except Exception:
            return fail('SEND_FAILED', 'Could not send the code', 500)
        # Mask the email in the response (privacy when phone was given)
        try:
            user_part, dom = email_to.split('@', 1)
            masked = (user_part[:2] + '***@' + dom)
        except Exception:
            masked = email_to
        return ok({'sent': True, 'channel': 'email', 'to': masked})

    @http.route('/api/mobile/v2/auth/otp/email/verify', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_email_verify(self, **kw):
        p = get_payload()
        target = (p.get('email') or p.get('email_or_phone') or '').strip().lower()
        code = (p.get('code') or '').strip()
        if not target or not code:
            return fail('MISSING_FIELDS', 'Email and code required', 400)
        if '@' not in target:
            # Phone → resolve to the account email (same as request step)
            Partner = request.env['res.partner'].sudo()
            digits = ''.join(ch for ch in target if ch.isdigit())
            pr = Partner.search(['|', ('phone', 'like', digits[-8:]),
                                 ('mobile', 'like', digits[-8:])], limit=1) \
                if len(digits) >= 8 else Partner.browse([])
            if not pr or not pr.email:
                return fail('NO_ACCOUNT', 'No account with this phone', 404)
            target = pr.email.lower()
        if not request.env['mobile.otp.code'].sudo().check(target, code):
            return fail('INVALID_CODE', 'Wrong or expired code', 401)
        Users = request.env['res.users'].sudo()
        user = Users.search([('login', '=', target)], limit=1)
        if not user:
            import secrets as _sec
            user = Users.with_context(no_reset_password=True).create({
                'name': (p.get('name') or target.split('@')[0]),
                'login': target,
                'email': target,
                'password': _sec.token_urlsafe(24),
                'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
            })
        token = issue_token(
            partner_id=user.partner_id.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({'token': token, 'user': _serialize_user(user.partner_id)})

    # ─── Combined OTP: email OR phone (SMS via Odoo IAP) ──────────────
    @http.route('/api/mobile/v2/auth/otp/send', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_send(self, **kw):
        """One endpoint for both channels. `target` with '@' → email code;
        digits → SMS code via Odoo's built-in SMS (IAP). Returns the
        channel used + masked destination."""
        import random
        p = get_payload()
        target = (p.get('target') or p.get('email_or_phone') or '').strip()
        if not target:
            return fail('MISSING_TARGET', 'Email or phone required', 400)
        code = '%06d' % random.randint(0, 999999)
        if '@' in target:
            email_to = target.lower()
            request.env['mobile.otp.code'].sudo().issue(email_to, code)
            try:
                request.env['mail.mail'].sudo().create({
                    'subject': 'Uellow sign-in code: %s' % code,
                    'email_to': email_to,
                    'body_html': (
                        '<div style="font-family:sans-serif">'
                        '<h2 style="color:#412402">Uellow</h2>'
                        '<p>Your sign-in code / رمز الدخول:</p>'
                        '<p style="font-size:30px;font-weight:bold;'
                        'letter-spacing:6px;color:#412402">%s</p>'
                        '<p>Valid for 10 minutes. صالح لمدة ١٠ دقائق.</p>'
                        '</div>') % code,
                }).send()
            except Exception:
                return fail('SEND_FAILED', 'Could not send the code', 500)
            u, d = email_to.split('@', 1)
            return ok({'sent': True, 'channel': 'email',
                       'to': u[:2] + '***@' + d})
        # Phone → SMS. Default country code +965 for bare 8-digit numbers.
        digits = ''.join(ch for ch in target if ch.isdigit())
        if len(digits) < 8:
            return fail('BAD_PHONE', 'Invalid phone number', 400)
        number = '+' + digits if not digits.startswith('00') else '+' + digits[2:]
        if len(digits) == 8:
            number = '+965' + digits
        request.env['mobile.otp.code'].sudo().issue(digits[-8:], code)
        try:
            sms = request.env['sms.sms'].sudo().create({
                'number': number,
                'body': 'Uellow code / رمز يلو: %s (10 min)' % code,
            })
            sms.send(unlink_failed=False, unlink_sent=False,
                     raise_exception=True)
            if sms.exists() and sms.state == 'error':
                raise Exception(sms.failure_type or 'sms error')
        except Exception as e:
            _logger.warning('OTP SMS send failed for %s: %s', number, e)
            return fail('SMS_FAILED',
                        'SMS could not be sent — try your email instead / '
                        'تعذر إرسال الرسالة — جرب بريدك الإلكتروني', 502)
        return ok({'sent': True, 'channel': 'sms',
                   'to': number[:4] + '*****' + number[-2:]})

    @http.route('/api/mobile/v2/auth/otp/check', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def otp_check(self, **kw):
        """Verify a code sent by /otp/send (email or SMS) and sign in,
        creating a portal account when the target is new."""
        p = get_payload()
        target = (p.get('target') or p.get('email_or_phone') or '').strip()
        code = (p.get('code') or '').strip()
        if not target or not code:
            return fail('MISSING_FIELDS', 'Target and code required', 400)
        Users = request.env['res.users'].sudo()
        if '@' in target:
            key = target.lower()
            if not request.env['mobile.otp.code'].sudo().check(key, code):
                return fail('INVALID_CODE', 'Wrong or expired code', 401)
            user = Users.search([('login', '=', key)], limit=1)
            if not user:
                import secrets as _sec
                user = Users.with_context(no_reset_password=True).create({
                    'name': (p.get('name') or key.split('@')[0]),
                    'login': key, 'email': key,
                    'password': _sec.token_urlsafe(24),
                    'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                })
        else:
            digits = ''.join(ch for ch in target if ch.isdigit())
            key = digits[-8:]
            if not request.env['mobile.otp.code'].sudo().check(key, code):
                return fail('INVALID_CODE', 'Wrong or expired code', 401)
            Partner = request.env['res.partner'].sudo()
            pr = Partner.search(['|', ('phone', 'like', key),
                                 ('mobile', 'like', key)], limit=1)
            user = (Users.search([('partner_id', '=', pr.id)], limit=1)
                    if pr else Users.browse([]))
            if not user:
                import secrets as _sec
                number = '+965' + key if len(digits) == 8 else '+' + digits
                login = 'otp-%s@uellow.app' % digits
                user = Users.with_context(no_reset_password=True).create({
                    'name': (p.get('name') or number),
                    'login': login,
                    'phone': number, 'mobile': number,
                    'password': _sec.token_urlsafe(24),
                    'groups_id': [(6, 0, [request.env.ref('base.group_portal').id])],
                })
        token = issue_token(
            partner_id=user.partner_id.id,
            device_id=p.get('device_id'),
            device_name=p.get('device_name'),
            push_token=p.get('push_token'),
            app_version=p.get('app_version'),
        )
        return ok({'token': token, 'user': _serialize_user(user.partner_id)})

    # ─── Forgot password ──────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/forgot', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def forgot_password(self, **kw):
        p = get_payload()
        email = (p.get('email') or '').strip().lower()
        if not email:
            return fail('MISSING_EMAIL', 'Email required')
        user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
        if user:
            try:
                user.action_reset_password()
            except Exception:
                pass
        # Always return success — never leak whether the email exists.
        return ok({'sent': True})

    # ─── Logout ───────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/auth/logout', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def logout(self, **kw):
        sess = current_session()
        if sess:
            sess.sudo().write({'is_active': False})
        return ok({'logged_out': True})

    # ─── Current user (token verify + fresh user object) ──────────────
    @http.route('/api/mobile/v2/auth/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        return ok({'user': _serialize_user(current_partner())})
