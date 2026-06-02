# -*- coding: utf-8 -*-
"""Shared helpers for /api/vendor/v1/* — same envelope as the customer
and driver APIs (success/data/meta or success:false/code/error)."""
import functools
import json
import logging
import traceback

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


CORS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS'),
    ('Access-Control-Allow-Headers',
     'Content-Type, Authorization, X-Requested-With, X-Lang, X-Device-Id'),
    ('Access-Control-Max-Age', '86400'),
]


def json_response(payload, status=200):
    body = json.dumps(payload, default=str, ensure_ascii=False).encode('utf-8')
    headers = [('Content-Type', 'application/json; charset=utf-8')] + CORS
    return request.make_response(body, headers=headers, status=status)


def ok(data=None, meta=None, status=200):
    out = {'success': True}
    if data is not None:
        out['data'] = data
    if meta is not None:
        out['meta'] = meta
    return json_response(out, status=status)


def fail(code, message='', status=400, **extra):
    out = {'success': False, 'code': code, 'error': message}
    out.update(extra)
    return json_response(out, status=status)


def safe_endpoint(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            if request.httprequest.method == 'OPTIONS':
                return json_response({'ok': True})
            return fn(*args, **kwargs)
        except Exception as exc:
            _logger.error('Vendor API %s failed: %s\n%s',
                          request.httprequest.path, exc, traceback.format_exc())
            return fail('SERVER_ERROR', str(exc), status=500)
    return wrapped


def get_payload():
    if request.httprequest.method == 'GET':
        return dict(request.httprequest.args)
    raw = request.httprequest.data
    if raw:
        try:
            return json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            pass
    return dict(request.params) if request.params else {}


def bearer_token():
    auth = request.httprequest.headers.get('Authorization', '') or ''
    if auth.lower().startswith('bearer '):
        return auth.split(' ', 1)[1].strip()
    return ''


def current_session():
    tok = bearer_token()
    if not tok:
        return request.env['vendor.session'].sudo().browse()
    sess = request.env['vendor.session'].sudo().find_by_token(tok)
    if sess:
        sess.touch(ip=request.httprequest.remote_addr or '')
    return sess


def current_vendor():
    sess = current_session()
    return sess.vendor_id if sess else request.env['uellow.vendor'].sudo().browse()


def require_auth(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        sess = current_session()
        if not sess or not sess.vendor_id:
            return fail('AUTH_REQUIRED', 'Authentication required', status=401)
        return fn(*args, **kwargs)
    return wrapped


def bilingual(record, field):
    if not record or field not in record._fields:
        return {'en': '', 'ar': ''}
    try:
        en = record.with_context(lang='en_US')[field]
        ar = record.with_context(lang='ar_001')[field]
    except Exception:
        en = ar = record[field] or ''
    if not isinstance(en, str):
        en = str(en or '')
    if not isinstance(ar, str):
        ar = str(ar or en or '')
    return {'en': en or ar or '', 'ar': ar or en or ''}


def fmt_price(amount, currency=None):
    cur = currency or request.env.company.currency_id
    sym = cur.symbol if cur else 'KD'
    return {
        'amount': round(float(amount or 0), cur.decimal_places if cur else 3),
        'currency': cur.name if cur else 'KWD',
        'symbol': sym,
        'digits': cur.decimal_places if cur else 3,
    }


def img_url(model, rec_id, field='image_256', unique=None):
    """Public Odoo image URL — same pattern as the customer API."""
    base = request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', '')
    u = f'/web/image/{model}/{rec_id}/{field}'
    if unique:
        import hashlib
        h = hashlib.md5(str(unique).encode()).hexdigest()[:8]
        u += f'?unique={h}'
    return u
