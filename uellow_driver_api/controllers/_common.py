# -*- coding: utf-8 -*-
"""Shared decorators + helpers for the driver API.

Same envelope as the customer mobile API: success / data / meta on
success, success:false / code / error on failure. ONE error path on the
Flutter side.
"""
import functools
import json
import logging
import traceback

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


CORS_HEADERS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS'),
    ('Access-Control-Allow-Headers',
        'Content-Type, Authorization, X-Requested-With, X-Lang, X-Device-Id'),
    ('Access-Control-Max-Age', '86400'),
]


def json_response(payload, status=200):
    body = json.dumps(payload, default=str, ensure_ascii=False).encode('utf-8')
    headers = [('Content-Type', 'application/json; charset=utf-8')] + CORS_HEADERS
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
            _logger.error('Driver API %s failed: %s\n%s',
                          request.httprequest.path, exc, traceback.format_exc())
            return fail('SERVER_ERROR', str(exc), status=500)
    return wrapped


def get_payload():
    """Parse JSON body OR form-encoded payload. Returns dict."""
    if request.httprequest.method in ('GET',):
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
    """Resolve the active driver.session from the Authorization header."""
    tok = bearer_token()
    if not tok:
        return request.env['driver.session'].sudo().browse()
    sess = request.env['driver.session'].sudo().find_by_token(tok)
    if sess:
        sess.touch(ip=request.httprequest.remote_addr or '')
    return sess


def current_driver():
    sess = current_session()
    return sess.driver_id if sess else request.env['delivery.driver'].sudo().browse()


def require_auth(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        sess = current_session()
        if not sess or not sess.driver_id:
            return fail('AUTH_REQUIRED', 'Authentication required', status=401)
        return fn(*args, **kwargs)
    return wrapped


# ─── Bilingual + money helpers ───────────────────────────────────────

def bilingual(record, field, ar_field=None):
    """Return {'en': ..., 'ar': ...} for a translated jsonb-style field."""
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
    sym = (cur.symbol if cur else 'KD')
    return {
        'amount':   round(float(amount or 0), cur.decimal_places if cur else 3),
        'currency': cur.name if cur else 'KWD',
        'symbol':   sym,
        'digits':   cur.decimal_places if cur else 3,
    }


def short_addr(partner):
    parts = [partner.street, partner.street2, partner.city,
             partner.country_id.name if partner.country_id else '']
    return ', '.join(p for p in parts if p)


def order_payment_method(order):
    """Best-effort 'cod' / 'knet' / 'paid' string for an order."""
    if (order.payment_term_id and 'cash' in (order.payment_term_id.name or '').lower()):
        return 'cod'
    last_tx = order.transaction_ids.filtered(
        lambda t: t.state in ('done', 'authorized'))[-1:] if order.transaction_ids else None
    if last_tx:
        code = (last_tx.provider_code or last_tx.provider_id.code or '').lower()
        if 'knet' in code or 'upayments' in code:
            return 'knet'
        return 'paid'
    return 'cod'


def order_status_code(line):
    """Unified driver-visible status code for a trip line."""
    if not line:
        return 'unknown'
    return {
        'pending':     'awaiting_pickup',
        'received':    'picked',
        'in_transit':  'out',
        'delivered':   'delivered',
        'failed':      'failed',
        'returned':    'returned',
        'cancelled':   'cancelled',
    }.get(line.delivery_status, line.delivery_status or 'unknown')


def status_label(code):
    """Bilingual status label for driver UI."""
    return {
        'awaiting_pickup': {'en': 'Awaiting pickup', 'ar': 'بانتظار الاستلام'},
        'picked':          {'en': 'Picked up',       'ar': 'تم الاستلام'},
        'out':             {'en': 'Out for delivery','ar': 'في الطريق'},
        'delivered':       {'en': 'Delivered',       'ar': 'تم التسليم'},
        'failed':          {'en': 'Failed',          'ar': 'فشل'},
        'returned':        {'en': 'Returned',        'ar': 'مرتجع'},
        'cancelled':       {'en': 'Cancelled',       'ar': 'ملغاة'},
    }.get(code, {'en': code, 'ar': code})
