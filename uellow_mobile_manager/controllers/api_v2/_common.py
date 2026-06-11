"""
Uellow Mobile API v2 — Common utilities
========================================

Shared building blocks for every v2 endpoint. Keeps endpoint files thin
and behaviour consistent (response shape, auth, error handling).

Response envelope (every endpoint, success OR failure):
    {
        "success": bool,
        "data":    <payload>            # only on success
        "error":   "Human readable",    # only on failure
        "code":    "ERR_INVALID_AUTH",  # only on failure — machine-friendly
        "meta":    { ... }              # pagination / hints / app messages
    }

Auth:
    Pass `Authorization: Bearer <token>` (or `X-App-Token` for legacy
    clients). Tokens are issued by /api/mobile/v2/auth/login and stored
    in `mobile.session`. `auth='public'` on every route — we authenticate
    via header explicitly so the same endpoint works for guests when
    appropriate.

Bilingual fields:
    Every user-facing label/title is returned as a dict with both
    languages, e.g. {"en": "...", "ar": "..."}. The Flutter side picks
    the active locale; no per-locale URL needed.
"""
import functools
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime

from odoo import fields
from odoo.http import request

_logger = logging.getLogger(__name__)

# Standard CORS headers — applied to every v2 response so the app can
# call from web previews / debug builds too.
CORS_HEADERS = [
    ('Content-Type', 'application/json; charset=utf-8'),
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'),
    ('Access-Control-Allow-Headers',
     'Content-Type, Authorization, X-App-Token, X-App-Version, X-Device-Id, X-Lang'),
    ('Access-Control-Max-Age', '86400'),
    ('Cache-Control', 'no-store'),
]


def _json(payload, status=200):
    """Serialize and wrap with CORS + standard headers."""
    return request.make_response(
        json.dumps(payload, ensure_ascii=False, default=str),
        headers=CORS_HEADERS,
        status=status,
    )


def ok(data=None, meta=None, status=200):
    body = {'success': True}
    if data is not None:
        body['data'] = data
    if meta is not None:
        body['meta'] = meta
    return _json(body, status)


def fail(code, message, status=400, extra=None):
    body = {'success': False, 'code': code, 'error': message}
    if extra:
        body.update(extra)
    return _json(body, status)


# ─── Request parsing ──────────────────────────────────────────────────

def get_payload():
    """Parse JSON body if any; otherwise return query params + form data.
    Robust to text/plain bodies (some Flutter http impls do that)."""
    raw = (request.httprequest.data or b'').decode('utf-8', 'replace').strip()
    body = {}
    if raw:
        try:
            body = json.loads(raw) or {}
        except Exception:
            body = {}
    # Merge URL params + form fields so endpoints can read either source.
    args = dict(request.httprequest.args.items())
    form = dict(request.httprequest.form.items())
    return {**args, **form, **body}


def get_lang():
    """Active language for this request. Order:
    1. ?lang= query
    2. X-Lang header
    3. session lang
    4. 'en_US'
    """
    args = request.httprequest.args
    headers = request.httprequest.headers
    lang = args.get('lang') or headers.get('X-Lang') or request.env.lang or 'en_US'
    if lang.startswith('ar'):
        return 'ar_001'
    return 'en_US'


def get_website():
    """Active website for this request — EVERYTHING (settings, builder
    pages, payment methods, carts, product publishing) is scoped per
    website. Order:
    1. X-Website-Id header (the app sends its selected website)
    2. ?website_id= query param
    3. first website (legacy fallback)
    """
    Website = request.env['website'].sudo()
    try:
        raw = (request.httprequest.headers.get('X-Website-Id')
               or request.httprequest.args.get('website_id') or 0)
        wid = int(raw)
        if wid:
            w = Website.browse(wid)
            if w.exists():
                return w
    except Exception:
        pass
    # Host-based: the app switches base domain per country
    # (kwapp.uellow.com, saapp.uellow.com, …) — match it to the website
    # whose `domain` ends with that host. Works with zero app changes.
    try:
        host = (request.httprequest.headers.get('X-Forwarded-Host')
                or request.httprequest.host or '').split(':')[0].lower()
        if host and 'localhost' not in host and '127.0.0.1' not in host:
            for w in Website.search([('domain', '!=', False)]):
                dom = (w.domain or '').lower()
                dom = dom.split('//')[-1].rstrip('/')
                if dom == host:
                    return w
    except Exception:
        pass
    try:
        return Website.search([], limit=1, order='id asc')
    except Exception:
        return Website.browse(1)


# Alias — clearer name at call sites.
current_website = get_website


def app_setting():
    """The mobile.app.setting row for the request's website (falls back to
    any row so a missing per-website config never breaks the app)."""
    S = request.env['mobile.app.setting'].sudo()
    try:
        w = get_website()
        rec = S.search([('website_id', '=', w.id)], limit=1)
        if rec:
            return rec
    except Exception:
        pass
    return S.search([], limit=1)


def base_url():
    """Absolute origin to prefix on outgoing URLs (images, share links, …).

    Order of preference:
      1. The host the client actually called us on — this respects the
         Cloudflare/proxy headers so production traffic always gets
         https://www.uellow.com even if the DB config gets reset to
         localhost:8069 by an Odoo restart without --proxy-mode.
      2. The `web.base.url` ir.config_parameter (fallback).
      3. Hardcoded production URL (last-resort safety net).
    """
    try:
        host = (request.httprequest.headers.get('X-Forwarded-Host')
                or request.httprequest.host)
        if host and 'localhost' not in host and '127.0.0.1' not in host:
            proto = (request.httprequest.headers.get('X-Forwarded-Proto')
                     or request.httprequest.scheme or 'https')
            return f'{proto}://{host}'.rstrip('/')
    except Exception:
        pass
    return request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', 'https://www.uellow.com'
    ).rstrip('/')


# Models whose images don't have a public ACL on /web/image — route
# them through our own public proxy so guests can load them.
_PROXY_MODELS = {
    'mobile.slider', 'mobile.category.icon', 'mobile.popup', 'mobile.section',
    'product.brand',
    # v2.1.66 — profile avatars: /web/image/res.partner is ACL-blocked for
    # the app's bearer (non-session) requests, so the account-page photo
    # never rendered. The proxy sudo-reads it (image_128/256 whitelisted).
    'res.partner',
    # v2.1.66 — vendor logo/banner never rendered on the vendor page for
    # the same reason.
    'uellow.vendor',
}

def img_url(model, rec_id, field='image_1024', unique=None):
    """Return a stable absolute image URL. Cache-busting `unique` is
    optional — pass record.write_date if you want it to change with the
    record."""
    if model in _PROXY_MODELS:
        u = f"{base_url()}/api/mobile/v2/img/{model}/{rec_id}/{field}"
    else:
        u = f"{base_url()}/web/image/{model}/{rec_id}/{field}"
    if unique:
        u += f"?unique={hashlib.md5(str(unique).encode()).hexdigest()[:8]}"
    return u


# v2.2.40 — brand attribute values store their logo on product.brand (matched
# by normalized name), NOT on product.attribute.value.image. This resolves the
# logo the same way the shop brands row / product page do, so filter chips can
# show the real brand image. Returns an absolute URL or None.
def brand_value_logo(value):
    for fld in ('dr_image', 'image'):
        if fld in value._fields and value[fld]:
            return img_url('product.attribute.value', value.id, fld,
                           unique=value.write_date)
    if 'product.brand' in request.env:
        cmp = (value.name or '').lower().replace(' ', '').replace('-', '')
        if cmp:
            for b in request.env['product.brand'].sudo().search([]):
                pn = (b.name or '').lower().replace(' ', '').replace('-', '')
                if pn == cmp and getattr(b, 'image_1024', False):
                    return img_url('product.brand', b.id, 'image_1024',
                                   unique=b.write_date)
    return None


def is_brand_attribute(attr):
    """True when an attribute is the brand/maker facet (bilingual names)."""
    nm = (attr.name or '').lower()
    return any(k in nm for k in ('brand', 'ماركة', 'علامة', 'براند'))


# ─── Bilingual helpers ────────────────────────────────────────────────

def bilingual(record, field, ar_field=None):
    """Read a field in both languages. Works on jsonb-translated fields
    OR on parallel `_ar` fields. Returns {"en": ..., "ar": ...}."""
    if not record:
        return {'en': '', 'ar': ''}
    try:
        en = record.with_context(lang='en_US')[field] or ''
        ar = record.with_context(lang='ar_001')[field] or en
        if ar_field and not ar:
            ar = record[ar_field] or en
        return {'en': en, 'ar': ar or en}
    except Exception:
        v = record[field] if field in record._fields else ''
        return {'en': v or '', 'ar': v or ''}


def t(record_or_dict, field, lang):
    """Convenience reader: returns the right language straight away."""
    if isinstance(record_or_dict, dict) and 'en' in record_or_dict:
        return record_or_dict.get('ar' if lang.startswith('ar') else 'en', '')
    if not record_or_dict:
        return ''
    try:
        return record_or_dict.with_context(lang=lang)[field] or ''
    except Exception:
        return ''


# ─── Authentication ───────────────────────────────────────────────────

def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(partner_id, device_id=None, device_name=None,
                push_token=None, app_version=None):
    """Create a fresh `mobile.session` and return the bearer token.

    The plaintext token is returned ONCE to the caller; only its sha256
    is stored, so a DB leak can't impersonate users."""
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    Session = request.env['mobile.session'].sudo()
    Session.create({
        'partner_id': partner_id,
        'token_hash': token_hash,
        'device_id': device_id or '',
        'device_name': device_name or '',
        'push_token': push_token or '',
        'app_version': app_version or '',
        'last_seen': fields.Datetime.now(),
        'is_active': True,
    })
    return token


def current_session():
    """Return the active `mobile.session` for this request — or False.
    Cached on the request object so multiple calls in one endpoint
    don't re-query."""
    if hasattr(request, '_mob_session_cache'):
        return request._mob_session_cache
    headers = request.httprequest.headers
    raw = headers.get('Authorization', '') or headers.get('X-App-Token', '')
    if raw.lower().startswith('bearer '):
        raw = raw[7:].strip()
    raw = raw.strip()
    sess = False
    if raw:
        token_hash = _hash_token(raw)
        sess = request.env['mobile.session'].sudo().search([
            ('token_hash', '=', token_hash),
            ('is_active', '=', True),
        ], limit=1)
        if sess:
            # Touch last_seen at most once per minute (cheap heartbeat)
            if not sess.last_seen or (fields.Datetime.now() - sess.last_seen).total_seconds() > 60:
                sess.sudo().write({'last_seen': fields.Datetime.now()})
    request._mob_session_cache = sess
    return sess


def current_partner():
    """Authenticated `res.partner` or False for guests."""
    sess = current_session()
    return sess and sess.partner_id or False


# ─── Decorators ───────────────────────────────────────────────────────

def require_auth(fn):
    """Block guests. Use on endpoints that REQUIRE a logged-in user.

    Endpoints that support both guest + auth (cart, search, products)
    should NOT use this — they should just call `current_partner()` and
    branch on the result."""
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_partner():
            return fail('AUTH_REQUIRED', 'Authentication required', status=401)
        return fn(*args, **kwargs)
    return wrapped


def safe_endpoint(fn):
    """Catch unhandled exceptions, log with context, return safe JSON.
    Prevents stack traces leaking through to the app."""
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            _logger.exception('Mobile API v2 %s failed: %s',
                              request.httprequest.path, e)
            return fail('SERVER_ERROR', str(e) or 'Unexpected server error',
                        status=500)
    return wrapped


# ─── Pagination ───────────────────────────────────────────────────────

def paginate(records, page, per_page, serializer):
    """Slice a recordset and return (items, meta)."""
    try:
        page = max(1, int(page))
    except Exception:
        page = 1
    try:
        per_page = min(100, max(1, int(per_page)))
    except Exception:
        per_page = 20
    total = len(records)
    start = (page - 1) * per_page
    end = start + per_page
    items = [serializer(r) for r in records[start:end]]
    return items, {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': (total + per_page - 1) // per_page,
        'has_next': end < total,
    }


# ─── Money / formatting ───────────────────────────────────────────────

# v2.1.86 — per-country display currency. The country app-websites share a
# KWD company, so the display currency is mapped by website id and prices are
# CONVERTED from the base (KWD) using res.currency rates. One central change →
# every price (cards, cart, detail, shipping, loyalty) shows the right currency.
_WEBSITE_CCY = {
    13: 'SAR', 3: 'SAR',          # Saudi (app / web)
    14: 'QAR',                    # Qatar
    15: 'AED', 7: 'AED',         # UAE
    16: 'EGP', 4: 'EGP',         # Egypt
    17: 'OMR', 9: 'OMR',         # Oman
    18: 'USD', 2: 'USD',         # USA
    # everything else → KWD (Kuwait / default)
}


def web_currency():
    """The display currency for the active website (per country)."""
    try:
        w = get_website()
        code = _WEBSITE_CCY.get(w.id)
        if code:
            c = request.env['res.currency'].sudo().with_context(
                active_test=False).search([('name', '=', code)], limit=1)
            if c:
                return c
        return w.currency_id or request.env.company.currency_id
    except Exception:
        return request.env.company.currency_id


def fmt_price(amount, currency=None):
    """Return both raw + display variants in the WEBSITE currency. `currency`
    is the SOURCE currency of `amount` (defaults to the company/KWD); the value
    is converted to the per-country display currency."""
    src = currency or request.env.company.currency_id
    dst = web_currency()
    try:
        amt = float(amount or 0)
    except Exception:
        amt = 0.0
    try:
        if src and dst and src.id != dst.id:
            from odoo import fields as _f
            amt = src._convert(amt, dst, request.env.company, _f.Date.today())
    except Exception:
        pass
    try:
        digits = dst.decimal_places if dst else 3
    except Exception:
        digits = 3
    return {
        'amount': round(amt, digits),
        'currency': dst.name if dst else 'KWD',
        'symbol': dst.symbol if dst else 'KD',
        'digits': digits,
    }
