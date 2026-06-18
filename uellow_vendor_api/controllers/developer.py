# -*- coding: utf-8 -*-
"""Vendor Open API — in-app management of API keys & webhooks.

These endpoints use the normal vendor session (Bearer token); they let the
vendor generate/revoke API keys and add/remove webhooks from the app. The
keys themselves authenticate the *public* API (see public_api.py)."""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor,
)

# Event catalogue mirrored to the app (code, EN, AR).
EVENTS = [
    ('new_order',        'New order',        'طلب جديد'),
    ('order_shipped',    'Order shipped',    'تم الشحن'),
    ('order_cancelled',  'Order cancelled',  'تم الإلغاء'),
    ('product_approved', 'Product approved', 'اعتماد منتج'),
    ('product_rejected', 'Product rejected', 'رفض منتج'),
    ('low_stock',        'Low stock',        'مخزون منخفض'),
]


def _ser_key(k):
    return {
        'id': k.id, 'name': k.name, 'prefix': k.key_prefix,
        'scope': k.scope, 'active': k.active,
        'last_used': k.last_used or '',
    }


def _ser_hook(h):
    return {
        'id': h.id, 'name': h.name, 'url': h.url,
        'events': (h.event_codes or '').split(',') if h.event_codes else [],
        'active': h.active, 'last_status': h.last_status or '',
        'last_error': h.last_error or '', 'fail_count': h.fail_count,
        'secret': h.secret or '',
    }


class VendorDeveloperController(http.Controller):

    def _guard(self, v):
        if not v.cap('api'):
            return fail('FORBIDDEN', 'API access is disabled for your account.',
                        403, capability='api')
        return None

    # ── catalogue ────────────────────────────────────────
    @http.route('/api/vendor/v1/dev/meta', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def dev_meta(self, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        base = request.httprequest.host_url.rstrip('/')
        return ok({
            'enabled': True,
            'events': [{'code': c, 'en': en, 'ar': ar} for c, en, ar in EVENTS],
            'base_url': base + '/api/public/v1',
            'docs': {
                'auth': 'Send header  X-API-Key: <your key>',
                'endpoints': ['GET /ping', 'GET /orders', 'GET /products',
                              'POST /products/<id>/stock {"qty": N}'],
                'webhook_signature': 'X-Uellow-Signature: sha256=HMAC(secret, body)',
            },
        })

    # ── API keys ─────────────────────────────────────────
    @http.route('/api/vendor/v1/dev/keys', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_keys(self, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        keys = request.env['vendor.api.key'].sudo().search([('vendor_id', '=', v.id)])
        return ok([_ser_key(k) for k in keys])

    @http.route('/api/vendor/v1/dev/keys/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_key(self, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        p = get_payload()
        scope = p.get('scope') if p.get('scope') in ('read', 'write') else 'read'
        raw, rec = request.env['vendor.api.key'].sudo().generate(
            v, name=(p.get('name') or 'API key'), scope=scope)
        # full secret returned exactly once
        return ok({'id': rec.id, 'key': raw, 'scope': scope,
                   'note': 'Store this now — it will not be shown again.'})

    @http.route('/api/vendor/v1/dev/keys/<int:kid>/revoke', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def revoke_key(self, kid, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        k = request.env['vendor.api.key'].sudo().browse(kid)
        if not k.exists() or k.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Key not found', 404)
        k.active = False
        return ok({'id': kid, 'active': False})

    # ── Webhooks ─────────────────────────────────────────
    @http.route('/api/vendor/v1/dev/webhooks', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_hooks(self, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        hooks = request.env['vendor.webhook'].sudo().search([('vendor_id', '=', v.id)])
        return ok([_ser_hook(h) for h in hooks])

    @http.route('/api/vendor/v1/dev/webhooks/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_hook(self, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        p = get_payload()
        url = (p.get('url') or '').strip()
        if not url:
            return fail('NO_URL', 'url required')
        Hook = request.env['vendor.webhook'].sudo()
        if not Hook._url_is_safe(url):
            return fail('UNSAFE_URL',
                        'URL must be public http(s) — internal/private hosts are blocked.')
        events = p.get('events') or ['new_order']
        if isinstance(events, str):
            events = [e.strip() for e in events.split(',') if e.strip()]
        valid = {c for c, _e, _a in EVENTS}
        events = [e for e in events if e in valid] or ['new_order']
        h = Hook.create({
            'name': (p.get('name') or 'Webhook'),
            'vendor_id': v.id,
            'url': url,
            'event_codes': ','.join(events),
        })
        return ok(_ser_hook(h))

    @http.route('/api/vendor/v1/dev/webhooks/<int:hid>/delete', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_hook(self, hid, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        h = request.env['vendor.webhook'].sudo().browse(hid)
        if not h.exists() or h.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Webhook not found', 404)
        h.unlink()
        return ok({'id': hid, 'deleted': True})

    @http.route('/api/vendor/v1/dev/webhooks/<int:hid>/test', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def test_hook(self, hid, **kw):
        v = current_vendor()
        g = self._guard(v)
        if g:
            return g
        h = request.env['vendor.webhook'].sudo().browse(hid)
        if not h.exists() or h.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Webhook not found', 404)
        if not h._url_is_safe(h.url):
            return fail('UNSAFE_URL', 'URL blocked by SSRF guard')
        delivered = h._post('ping', {'message': 'Test delivery from Uellow', 'vendor_id': v.id})
        return ok({'delivered': delivered, 'last_status': h.last_status,
                   'last_error': h.last_error or ''})
