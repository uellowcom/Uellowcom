# -*- coding: utf-8 -*-
import json
import logging
import requests
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# ── Correct Taly API URLs from official docs ──────────────────────────────────
TALY_SANDBOX_URL  = 'https://api.dev-taly.io'   # Sandbox / Test
TALY_PROD_URL     = 'https://api.taly.io'        # Production

# Fixed Basic Auth header required by Taly OAuth2 server
TALY_BASIC_AUTH   = 'Basic bWVyY2hhbnQ6c2VjcmV0'

TALY_ORDER_STATUSES = {
    'CONFIRMED':  'done',
    'PAID':       'done',
    'APPROVED':   'done',
    'PENDING':    'pending',
    'PROCESSING': 'pending',
    'FAILED':     'cancel',
    'REJECTED':   'cancel',
    'CANCELLED':  'cancel',
    'EXPIRED':    'cancel',
    'REFUNDED':   'cancel',
}


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('taly', 'Taly - الدفع بالأقساط')],
        ondelete={'taly': 'set default'},
    )

    # ── Credentials ───────────────────────────────────────────────────────────
    taly_api_username = fields.Char(
        string='API Username (Merchant Key)',
        help='Merchant API username from Taly Partners Portal → Settings → Keys',
    )
    taly_api_password = fields.Char(
        string='API Secret Key',
        groups='base.group_system',
        help='Merchant API secret key from Taly Partners Portal → Settings → Keys',
    )
    taly_webhook_secret = fields.Char(
        string='Webhook Secret Key',
        groups='base.group_system',
        help='Webhook secret key (UUID) from Taly Partners Portal',
    )

    # ── Widget / Display ──────────────────────────────────────────────────────
    taly_installment_type = fields.Selection(
        selection=[('3', 'Split in 3'), ('4', 'Split in 4')],
        string='Installment Plan',
        default='3',
    )
    taly_widget_lang = fields.Selection(
        selection=[('ar', 'العربية'), ('en', 'English')],
        string='Widget Language',
        default='ar',
    )
    taly_show_widget_product = fields.Boolean(
        string='Show Widget on Product Pages',
        default=True,
    )
    taly_show_widget_cart = fields.Boolean(
        string='Show Widget on Cart Page',
        default=True,
    )
    taly_min_order_amount = fields.Float(string='Minimum Order Amount', default=0.0)
    taly_max_order_amount = fields.Float(string='Maximum Order Amount', default=0.0)

    # ── Token cache ───────────────────────────────────────────────────────────
    taly_token_cache        = fields.Char(string='Cached Access Token',  groups='base.group_system')
    taly_refresh_token      = fields.Char(string='Cached Refresh Token', groups='base.group_system')
    taly_token_expiry       = fields.Datetime(string='Access Token Expiry',  groups='base.group_system')
    taly_refresh_expiry     = fields.Datetime(string='Refresh Token Expiry', groups='base.group_system')

    # ── Statistics ────────────────────────────────────────────────────────────
    taly_tx_count           = fields.Integer(string='Total Transactions',       compute='_compute_taly_stats')
    taly_tx_done_count      = fields.Integer(string='Successful Transactions',  compute='_compute_taly_stats')
    taly_tx_pending_count   = fields.Integer(string='Pending Transactions',     compute='_compute_taly_stats')
    taly_tx_cancel_count    = fields.Integer(string='Cancelled Transactions',   compute='_compute_taly_stats')
    taly_total_amount       = fields.Float(  string='Total Amount Processed',   compute='_compute_taly_stats')

    @api.depends('code')
    def _compute_taly_stats(self):
        for rec in self:
            if rec.code != 'taly':
                rec.taly_tx_count = rec.taly_tx_done_count = 0
                rec.taly_tx_pending_count = rec.taly_tx_cancel_count = 0
                rec.taly_total_amount = 0.0
                continue
            txs = self.env['payment.transaction'].search([('provider_id', '=', rec.id)])
            done = txs.filtered(lambda t: t.state == 'done')
            rec.taly_tx_count        = len(txs)
            rec.taly_tx_done_count   = len(done)
            rec.taly_tx_pending_count = len(txs.filtered(lambda t: t.state == 'pending'))
            rec.taly_tx_cancel_count  = len(txs.filtered(lambda t: t.state == 'cancel'))
            rec.taly_total_amount     = sum(done.mapped('amount'))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _taly_base_url(self):
        return TALY_SANDBOX_URL if self.state == 'test' else TALY_PROD_URL

    def _taly_get_token(self):
        """
        OAuth2 password-grant authentication.
        Endpoint: POST /uaa/oauth/token
        Header:   Authorization: Basic bWVyY2hhbnQ6c2VjcmV0
        Body:     x-www-form-urlencoded  username / password / grant_type=password / scope=ui
        Token valid 15 min; refresh token valid 30 min.
        """
        self.ensure_one()
        now = fields.Datetime.now()

        # 1. Use cached access token if still valid (with 1-min buffer)
        if (self.taly_token_cache and self.taly_token_expiry
                and self.taly_token_expiry > now + timedelta(minutes=1)):
            return self.taly_token_cache

        # 2. Try refresh token if still valid
        if (self.taly_refresh_token and self.taly_refresh_expiry
                and self.taly_refresh_expiry > now + timedelta(minutes=1)):
            token_data = self._taly_oauth_call(grant_type='refresh_token',
                                                refresh_token=self.taly_refresh_token)
            if token_data:
                self._taly_store_tokens(token_data)
                return self.taly_token_cache

        # 3. Full login
        if not self.taly_api_username or not self.taly_api_password:
            raise UserError(_("Taly: يرجى إدخال API Username و Secret Key أولاً."))

        token_data = self._taly_oauth_call(
            grant_type='password',
            username=self.taly_api_username,
            password=self.taly_api_password,
        )
        if not token_data:
            raise UserError(_("Taly: فشل الحصول على token."))

        self._taly_store_tokens(token_data)
        self._taly_log('auth/login', 'success', 'Authentication successful')
        return self.taly_token_cache

    def _taly_oauth_call(self, grant_type, **kwargs):
        """Raw OAuth2 token call."""
        url = f"{self._taly_base_url()}/uaa/oauth/token"
        payload = {'grant_type': grant_type, 'scope': 'ui'}
        payload.update(kwargs)
        try:
            resp = requests.post(
                url,
                data=payload,                          # form-urlencoded
                headers={
                    'Authorization': TALY_BASIC_AUTH,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout=15,
            )
            _logger.info("Taly OAuth %s → %s", grant_type, resp.status_code)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self._taly_log('auth/login', 'error', str(e))
            raise UserError(_("Taly: فشل الاتصال بـ API\n%s") % str(e))

    def _taly_store_tokens(self, data):
        """Persist access_token and refresh_token with expiry times."""
        now = datetime.now()
        access_expires_in  = int(data.get('expires_in', 900))        # default 15 min
        refresh_expires_in = int(data.get('refresh_expires_in', 1800))  # default 30 min
        self.sudo().write({
            'taly_token_cache':    data.get('access_token'),
            'taly_refresh_token':  data.get('refresh_token'),
            'taly_token_expiry':   now + timedelta(seconds=access_expires_in - 30),
            'taly_refresh_expiry': now + timedelta(seconds=refresh_expires_in - 30),
        })

    def _taly_api_call(self, method, endpoint, payload=None, token=None):
        """Authenticated JSON API call."""
        self.ensure_one()
        if not token:
            token = self._taly_get_token()
        url = f"{self._taly_base_url()}{endpoint}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type':  'application/json',
            'Accept':        'application/json',
        }
        try:
            resp = requests.request(method, url, json=payload, headers=headers, timeout=20)
            _logger.info("Taly API %s %s → %s", method, endpoint, resp.status_code)
            self._taly_log(endpoint, 'success' if resp.ok else 'error',
                           resp.text[:1000], payload=json.dumps(payload or {}))
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            self._taly_log(endpoint, 'error', str(e), payload=json.dumps(payload or {}))
            raise UserError(_("Taly API Error: %s") % str(e))

    def _taly_create_order(self, transaction):
        """
        POST /accounts/payment/v2/initiate
        Returns (checkout_url, taly_order_id, order_token)
        """
        self.ensure_one()
        base_url = self.get_base_url()
        payload = {
            'merchantOrderId': transaction.reference,
            'amount':          round(transaction.amount, 3),
            'currency':        transaction.currency_id.name,
            'customer': {
                'firstName': (transaction.partner_name or '').split()[0] or '',
                'lastName':  ' '.join((transaction.partner_name or '').split()[1:]) or '',
                'email':     transaction.partner_email or '',
                'phone':     transaction.partner_phone or '',
            },
            'redirectUrl': f"{base_url}/payment/taly/return",
            'postBackUrl': f"{base_url}/payment/taly/webhook",
        }
        data = self._taly_api_call('POST', '/accounts/payment/v2/initiate', payload=payload)
        checkout_url = data.get('checkoutUrl') or data.get('checkout_url')
        order_id     = data.get('orderId')     or data.get('id')
        order_token  = data.get('orderToken')
        return checkout_url, order_id, order_token

    def _taly_get_order(self, merchant_order_id):
        """GET /accounts/merchant/orders?merchantOrderId=..."""
        self.ensure_one()
        data = self._taly_api_call(
            'GET',
            f'/accounts/merchant/orders?merchantOrderId={merchant_order_id}',
        )
        return data.get('data') or data

    def _taly_refund_order(self, order_token, amount=None, reason='Refund from Odoo'):
        """PUT /accounts/merchant/orders/refund"""
        self.ensure_one()
        payload = {'orderToken': order_token, 'reason': reason}
        if amount:
            payload['amount'] = round(amount, 3)
        return self._taly_api_call('PUT', '/accounts/merchant/orders/refund', payload=payload)

    def _taly_log(self, action, status, message, payload=''):
        self.env['payment.taly.log'].sudo().create({
            'provider_id': self.id,
            'action':  action[:64],
            'status':  status,
            'message': message,
            'payload': payload,
        })

    # ── Odoo payment framework ────────────────────────────────────────────────

    def _get_supported_currencies(self):
        supported = super()._get_supported_currencies()
        if self.code == 'taly':
            supported = supported.filtered(
                lambda c: c.name in ('KWD', 'SAR', 'AED', 'USD', 'BHD', 'QAR', 'OMR')
            )
        return supported

    def action_test_connection(self):
        self.ensure_one()
        if self.code != 'taly':
            raise UserError(_("This action is only for Taly provider."))
        # Clear cache to force fresh login
        self.sudo().write({
            'taly_token_cache':   False,
            'taly_refresh_token': False,
            'taly_token_expiry':  False,
            'taly_refresh_expiry': False,
        })
        token = self._taly_get_token()
        if token:
            return {
                'type': 'ir.actions.client',
                'tag':  'display_notification',
                'params': {
                    'title':   _('Taly Connection'),
                    'message': _('✅ تم الاتصال بـ Taly بنجاح!'),
                    'type':    'success',
                    'sticky':  False,
                },
            }

    def action_view_taly_transactions(self):
        return {
            'name':      _('Taly Transactions'),
            'type':      'ir.actions.act_window',
            'res_model': 'payment.transaction',
            'view_mode': 'list,form',
            'domain':    [('provider_id', '=', self.id)],
        }

    def action_view_taly_logs(self):
        return {
            'name':      _('Taly API Logs'),
            'type':      'ir.actions.act_window',
            'res_model': 'payment.taly.log',
            'view_mode': 'list,form',
            'domain':    [('provider_id', '=', self.id)],
        }

    def action_taly_dashboard(self):
        return {
            'name':      _('Taly Dashboard'),
            'type':      'ir.actions.act_window',
            'res_model': 'payment.provider',
            'res_id':    self.id,
            'view_mode': 'form',
            'views':     [(self.env.ref('payment_taly.view_taly_dashboard_form').id, 'form')],
        }
