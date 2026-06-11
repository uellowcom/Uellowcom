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
    # success
    'CONFIRMED':  'done',
    'PAID':       'done',
    'APPROVED':   'done',
    'SUCCESS':    'done',      # value sent on the merchant redirect URL
    'COMPLETED':  'done',
    # pending / in-flight
    'PENDING':    'pending',
    'PROCESSING': 'pending',
    'INITIATED':  'pending',
    # failure / cancellation
    'FAILED':     'cancel',
    'FAILURE':    'cancel',    # value sent on the merchant redirect URL
    'REJECTED':   'cancel',
    'CANCEL':     'cancel',    # value sent on the merchant redirect URL
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
    taly_min_order_amount = fields.Float(
        string='Minimum Order Amount', default=10.0,
        help='Taly only allows orders at or above this amount. Default 10 KWD '
             '— الحد الأدنى لطلب تالي (افتراضياً ١٠ د.ك). Customers below this '
             'cannot complete the payment with Taly.')
    taly_max_order_amount = fields.Float(string='Maximum Order Amount', default=0.0)

    def _taly_check_amount(self, amount):
        """Raise a clear bilingual error when below the configured minimum."""
        self.ensure_one()
        min_amt = self.taly_min_order_amount or 0.0
        if min_amt and float(amount or 0.0) < min_amt:
            cur = self.company_id.currency_id.name or 'KWD'
            raise UserError(_(
                "Taly requires a minimum order of %(m).3f %(c)s. "
                "أقل مبلغ للدفع بالأقساط عبر تالي هو %(m).3f %(c)s.",
                m=min_amt, c=cur))

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
            if not resp.ok:
                # v2.2.27 — surface the REAL Taly error (was swallowed as a
                # generic "connection failed", which hid e.g. wrong env:
                # production keys fail on the sandbox base with
                # invalid_grant/Bad credentials).
                self._taly_log('auth/login', 'error',
                               '%s %s' % (resp.status_code, resp.text[:500]))
                raise UserError(_(
                    "Taly authentication failed (%s).\n%s\n\n"
                    "Tip: a 'Bad credentials' error usually means the keys "
                    "belong to a different environment — production keys do "
                    "not work while the provider is in Test mode, and vice "
                    "versa."
                ) % (resp.status_code, resp.text[:300]))
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
            if not resp.ok:
                # v2.2.27 — include the real Taly error body in the message.
                raise UserError(_("Taly API Error (%s %s): %s")
                                % (method, endpoint, resp.text[:400]))
            return resp.json()
        except requests.RequestException as e:
            self._taly_log(endpoint, 'error', str(e), payload=json.dumps(payload or {}))
            raise UserError(_("Taly API Error: %s") % str(e))

    @staticmethod
    def _taly_split_phone(phone):
        """Return (countryCode, nationalNumber). Taly wants them separate."""
        p = ''.join(ch for ch in (phone or '') if ch.isdigit() or ch == '+')
        digits = p.lstrip('+').lstrip('0')
        # Common GCC country codes (longest first to avoid mis-splits).
        for cc in ('965', '966', '971', '973', '974', '968', '970', '20'):
            if digits.startswith(cc) and len(digits) > len(cc):
                return cc, digits[len(cc):]
        return '965', (digits or '00000000')

    def _taly_order_items(self, transaction):
        """Build the orderItems array from the linked sale order(s). Each
        item needs name + nameArabic + quantity + itemPrice (Taly-required).
        Falls back to a single synthetic line if no SO is linked."""
        items = []
        try:
            ar = self.env['res.lang'].sudo().search(
                [('code', '=like', 'ar%'), ('active', '=', True)], limit=1).code
            for so in transaction.sale_order_ids:
                for ln in so.order_line:
                    if ln.display_type or not ln.product_id:
                        continue
                    prod = ln.product_id
                    name = (prod.name or 'Item')[:255]
                    name_ar = name
                    if ar:
                        try:
                            name_ar = (prod.with_context(lang=ar).name
                                       or name)[:255]
                        except Exception:
                            name_ar = name
                    items.append({
                        'name': name,
                        'nameArabic': name_ar,
                        'quantity': int(ln.product_uom_qty or 1),
                        'itemPrice': round(ln.price_unit or 0.0, 3),
                        'sku': (prod.default_code or '')[:128],
                        'type': 'physical',
                    })
        except Exception:
            _logger.debug('taly order items build failed', exc_info=True)
        if not items:
            items = [{
                'name': transaction.reference or 'Order',
                'nameArabic': transaction.reference or 'طلب',
                'quantity': 1,
                'itemPrice': round(transaction.amount, 3),
                'type': 'physical',
            }]
        return items

    def _taly_create_order(self, transaction):
        """
        POST /accounts/payment/v2/initiate  (schema per docs.taly.io)
        Returns (checkout_url, taly_order_id, order_token).
        """
        self.ensure_one()
        self._taly_check_amount(transaction.amount)
        base_url = self.get_base_url()
        cc, pnum = self._taly_split_phone(transaction.partner_phone)
        full = (transaction.partner_name or transaction.partner_id.name or '').strip()
        parts = full.split()
        first = parts[0] if parts else 'Customer'
        last = ' '.join(parts[1:]) if len(parts) > 1 else '.'
        lang = (transaction.partner_id.lang or 'ar')[:2].lower()
        amount = round(transaction.amount, 3)
        payload = {
            'merchantOrderId': transaction.reference,
            'currency':        transaction.currency_id.name,
            'language':        'ar' if lang == 'ar' else 'en',
            'subTotal':        amount,
            'taxAmount':       0.0,
            'discountAmount':  0.0,
            'deliveryAmount':  0.0,
            'totalAmount':     amount,
            'deliveryMethod':  'Delivery',
            'merchantRedirectUrl': f"{base_url}/payment/taly/return",
            'postBackUrl':         f"{base_url}/payment/taly/webhook",
            'platform':        'website',
            'customerDetails': {
                'firstName':     first or 'Customer',
                'lastName':      last or '.',
                'countryCode':   cc,
                'phoneNumber':   pnum,
                'customerEmail': transaction.partner_email or 'noemail@uellow.com',
            },
            'orderItems':      self._taly_order_items(transaction),
        }
        data = self._taly_api_call('POST', '/accounts/payment/v2/initiate', payload=payload)
        # Real response keys: secureCheckoutUrl / talyOrderId / orderToken.
        checkout_url = (data.get('secureCheckoutUrl') or data.get('checkoutUrl')
                        or data.get('checkout_url'))
        order_id = (data.get('talyOrderId') or data.get('orderId')
                    or data.get('id'))
        order_token = data.get('orderToken')
        return checkout_url, (str(order_id) if order_id else False), order_token

    def _taly_get_order(self, merchant_order_id):
        """GET /accounts/merchant/orders?merchantOrderId=...
        NOTE: keyed by the MERCHANT order id (our tx.reference), not the
        Taly order token."""
        self.ensure_one()
        data = self._taly_api_call(
            'GET',
            f'/accounts/merchant/orders?merchantOrderId={merchant_order_id}',
        )
        return data.get('data') or data

    @api.model
    def _taly_open_dashboard(self):
        """v2.2.27 — open the single Taly provider's dashboard form directly
        (the menu action used to open a blank create-form → /new)."""
        prov = self.sudo().search([('code', '=', 'taly')], limit=1)
        if not prov:
            return {'type': 'ir.actions.act_window',
                    'res_model': 'payment.provider', 'view_mode': 'list',
                    'domain': [('code', '=', 'taly')], 'target': 'current'}
        return {
            'type': 'ir.actions.act_window', 'res_model': 'payment.provider',
            'res_id': prov.id, 'view_mode': 'form',
            'views': [(self.env.ref(
                'payment_taly.view_taly_dashboard_form').id, 'form')],
            'target': 'current', 'name': 'Taly Dashboard',
        }

    @api.model
    def _taly_open_settings(self):
        """Open the single Taly provider's configuration form directly."""
        prov = self.sudo().search([('code', '=', 'taly')], limit=1)
        if not prov:
            return {'type': 'ir.actions.act_window',
                    'res_model': 'payment.provider', 'view_mode': 'list',
                    'domain': [('code', '=', 'taly')], 'target': 'current'}
        return {
            'type': 'ir.actions.act_window', 'res_model': 'payment.provider',
            'res_id': prov.id, 'view_mode': 'form',
            'target': 'current', 'name': 'Taly Settings',
        }

    def _taly_order_status(self, merchant_order_id):
        """Return the normalized Odoo state ('done'/'pending'/'cancel'/'') for
        a merchant order id — used by the POS to poll an in-store session."""
        self.ensure_one()
        data = self._taly_get_order(merchant_order_id) or {}
        raw = (data.get('status') or data.get('orderStatus')
               or data.get('paymentStatus') or '').upper()
        return TALY_ORDER_STATUSES.get(raw, ''), raw

    def _taly_create_instore_session(self, vals):
        """
        POST /accounts/payment/in-store/checkout-session  (POS).
        Creates an in-store order; Taly auto-sends the customer an SMS
        payment link (valid 15 min). Returns the parsed response:
        {orderToken, securePaymentLink, merchantOrderId, expiryTime, totalAmount}.

        `vals` must carry: merchant_order_id, amount, currency, language,
        first_name, last_name, email, country_code, phone, redirect_url,
        post_back_url, items(optional), store(optional).
        """
        self.ensure_one()
        amount = round(float(vals.get('amount') or 0.0), 3)
        self._taly_check_amount(amount)
        cc, pnum = self._taly_split_phone(vals.get('phone'))
        payload = {
            'merchantOrderId': vals['merchant_order_id'],
            'language':        'AR' if (vals.get('language') or 'ar')[:2].lower() == 'ar' else 'EN',
            'otherFee':        0,
            'subTotal':        amount,
            'taxAmount':       0.0,
            'totalAmount':     amount,
            'currency':        vals.get('currency') or 'KWD',
            'customerDetails': {
                'customerEmail': vals.get('email') or 'noemail@uellow.com',
                'firstName':     vals.get('first_name') or 'Customer',
                'lastName':      vals.get('last_name') or '.',
                'gender':        vals.get('gender') or 'M',
                'phoneNumber':   pnum,
                'countryCode':   '+' + cc,
            },
            'merchantRedirectUrl': vals.get('redirect_url') or self.get_base_url(),
            'orderItems':      vals.get('items') or None,
            'storeNameOrCode': vals.get('store') or None,
            'postBackUrl':     vals.get('post_back_url')
                               or (self.get_base_url() + '/payment/taly/webhook'),
        }
        data = self._taly_api_call(
            'POST', '/accounts/payment/in-store/checkout-session', payload=payload)
        return {
            'orderToken':       data.get('orderToken'),
            'securePaymentLink': (data.get('securePaymentLink')
                                  or data.get('secureCheckoutUrl')),
            'merchantOrderId':  data.get('merchantOrderId') or vals['merchant_order_id'],
            'expiryTime':       data.get('expiryTime'),
            'totalAmount':      data.get('totalAmount') or amount,
        }

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
