# -*- coding: utf-8 -*-
"""Vendor Open API — per-vendor API keys + outbound webhooks.

Lets a vendor integrate Uellow with their own ERP / store: authenticate REST
calls with an API key, and receive real-time events (new order, product
approved, …) as signed HTTP webhooks.
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import socket
from urllib.parse import urlparse

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Event catalogue (code → human label). Kept here so views, dispatch and the
# app all agree on the same set.
WEBHOOK_EVENTS = [
    ('new_order',        'New order'),
    ('order_shipped',    'Order shipped'),
    ('order_cancelled',  'Order cancelled'),
    ('product_approved', 'Product approved'),
    ('product_rejected', 'Product rejected'),
    ('low_stock',        'Low stock'),
]


def _sha256(s):
    return hashlib.sha256((s or '').encode()).hexdigest()


class VendorApiKey(models.Model):
    _name = 'vendor.api.key'
    _description = 'Vendor API Key'
    _order = 'create_date desc'

    name = fields.Char('Label', required=True, default='API key')
    vendor_id = fields.Many2one('uellow.vendor', required=True, ondelete='cascade', index=True)
    key_prefix = fields.Char('Key Prefix', readonly=True, index=True,
                             help='Visible, non-secret prefix of the key (uk_live_xxxx…).')
    token_hash = fields.Char('Token Hash', readonly=True, index=True)
    scope = fields.Selection([('read', 'Read only'), ('write', 'Read & write')],
                             default='read', required=True, string='Scope')
    active = fields.Boolean(default=True)
    last_used = fields.Datetime('Last Used', readonly=True)

    @api.model
    def generate(self, vendor, name='API key', scope='read'):
        """Create a key and return (full_plaintext_key, record).
        The plaintext is shown ONCE — only its hash is stored."""
        raw = 'uk_live_' + secrets.token_urlsafe(32)
        rec = self.sudo().create({
            'name': name or 'API key',
            'vendor_id': vendor.id,
            'key_prefix': raw[:14],
            'token_hash': _sha256(raw),
            'scope': scope if scope in ('read', 'write') else 'read',
        })
        return raw, rec

    @api.model
    def authenticate(self, raw_key):
        """Return the live (vendor, key) for a plaintext key, or (None, None)."""
        if not raw_key:
            return None, None
        rec = self.sudo().search(
            [('token_hash', '=', _sha256(raw_key.strip())), ('active', '=', True)], limit=1)
        if not rec or rec.vendor_id.state == 'suspended':
            return None, None
        rec.sudo().last_used = fields.Datetime.now()
        return rec.vendor_id, rec


class VendorWebhook(models.Model):
    _name = 'vendor.webhook'
    _description = 'Vendor Webhook Subscription'
    _order = 'create_date desc'

    name = fields.Char('Label', required=True, default='Webhook')
    vendor_id = fields.Many2one('uellow.vendor', required=True, ondelete='cascade', index=True)
    url = fields.Char('Endpoint URL', required=True)
    secret = fields.Char('Signing Secret', readonly=True,
                         help='Used to HMAC-SHA256 sign each payload (X-Uellow-Signature).')
    event_codes = fields.Char('Events', default='new_order',
                              help='Comma-separated event codes this endpoint receives.')
    active = fields.Boolean(default=True)
    last_status = fields.Char('Last Status', readonly=True)
    last_error = fields.Char('Last Error', readonly=True)
    last_delivery = fields.Datetime('Last Delivery', readonly=True)
    fail_count = fields.Integer('Consecutive Failures', readonly=True, default=0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('secret'):
                vals['secret'] = 'whsec_' + secrets.token_urlsafe(24)
        return super().create(vals_list)

    # ── SSRF guard ───────────────────────────────────────
    @staticmethod
    def _url_is_safe(url):
        """Block non-http(s), localhost and private / link-local / reserved IPs
        to stop webhooks being pointed at internal services."""
        try:
            p = urlparse(url)
        except Exception:
            return False
        if p.scheme not in ('http', 'https') or not p.hostname:
            return False
        try:
            infos = socket.getaddrinfo(p.hostname, None)
        except Exception:
            return False
        for info in infos:
            ip = info[4][0]
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                return False
            if (addr.is_private or addr.is_loopback or addr.is_link_local
                    or addr.is_multicast or addr.is_reserved or addr.is_unspecified):
                return False
        return True

    def _post(self, event, payload):
        """Best-effort signed POST. Never raises (caller is in a live txn)."""
        self.ensure_one()
        import requests  # local import → no hard dep at module load
        body = json.dumps({'event': event, 'data': payload}, default=str)
        sig = hmac.new((self.secret or '').encode(), body.encode(),
                       hashlib.sha256).hexdigest()
        headers = {
            'Content-Type': 'application/json',
            'X-Uellow-Event': event,
            'X-Uellow-Signature': 'sha256=' + sig,
        }
        try:
            r = requests.post(self.url, data=body, headers=headers, timeout=4)
            ok = 200 <= r.status_code < 300
            self.sudo().write({
                'last_status': str(r.status_code),
                'last_error': '' if ok else (r.text or '')[:200],
                'last_delivery': fields.Datetime.now(),
                'fail_count': 0 if ok else (self.fail_count + 1),
            })
            return ok
        except Exception as e:
            self.sudo().write({
                'last_status': 'error',
                'last_error': str(e)[:200],
                'last_delivery': fields.Datetime.now(),
                'fail_count': self.fail_count + 1,
            })
            return False

    @api.model
    def dispatch(self, vendor_id, event, payload):
        """Fire `event` to every active webhook of `vendor_id` subscribed to it.
        Globally gated by ir.config_parameter uellow.vendor_api.webhooks_enabled
        (default on). Best-effort — swallows all errors."""
        param = self.env['ir.config_parameter'].sudo()
        if param.get_param('uellow.vendor_api.webhooks_enabled', 'True') == 'False':
            return
        try:
            hooks = self.sudo().search([
                ('vendor_id', '=', vendor_id), ('active', '=', True),
            ])
            for h in hooks:
                if event not in (h.event_codes or '').split(','):
                    continue
                if not h._url_is_safe(h.url):
                    h.sudo().write({'last_status': 'blocked',
                                    'last_error': 'URL blocked (SSRF guard)',
                                    'last_delivery': fields.Datetime.now()})
                    continue
                h._post(event, payload)
        except Exception:
            _logger.exception('Webhook dispatch failed for vendor %s event %s',
                              vendor_id, event)
