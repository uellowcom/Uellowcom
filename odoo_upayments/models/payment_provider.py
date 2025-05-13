# -*- coding: utf-8 -*-

import bcrypt
import pprint
import logging
import requests
import base64
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.addons.odoo_upayments.const import SUPPORTED_CURRENCIES
from odoo.addons.odoo_upayments import const
from urllib.parse import urlparse, parse_qs
from requests.exceptions import HTTPError, ConnectionError, Timeout
from odoo import tools

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('upayments', "UPayments")], ondelete={'upayments': 'set default'})
    api_type = fields.Selection([('white_label', 'White Label'), ('non_white_label', 'Non White Label')])
    upay_application_key = fields.Char(string='Application Key', required_if_provider='upayments')
    error_msg = fields.Html(
        string="Error Message",
        help="The message displayed if the order is canceled during the payment process due to error occur.",
        default=lambda self: _("Your payment has been cancelled due to error occur."),
        translate=True
    )

    @api.constrains('upay_application_key')
    def set_api_type(self):
        """ it is just only for set or update payment (white label or not-white label) """
        if self.code == 'upayments' and self.upay_application_key and self.state != 'disabled':
            result = self.get_all_payment_method()
            if result and result['data']['isWhiteLabel']:
                self.api_type = 'white_label'
            else:
                self.api_type = 'non_white_label'

    @api.constrains('state', 'api_type')
    def _set_or_update_payment_method(self):
        if self.state != 'disabled' and self.code == 'upayments':
            self.update_payment_provider_method()

    def _get_supported_currencies(self):
        """ return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'upayments':
            supported_currencies = supported_currencies.filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)
        return supported_currencies

    def _upayments_make_request(self, payload=None, method='POST'):
        """ Make a request at UPayments endpoint """
        self.ensure_one()
        url = self._upayments_get_api_url()
        if self.state == "enabled":
            api_key = self.upay_application_key.encode('utf-8')
            payload.update({'api_key': bcrypt.hashpw(api_key, bcrypt.gensalt()).decode('utf-8')})
        else:
            payload.update({'api_key': self.upay_application_key})

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.upay_application_key}',
        }
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(f"Invalid API request at {url} with data:\n{pprint.pformat(payload)}")
                raise ValidationError(
                    f"UPayments: The communication with the API failed."
                    f" UPayments gave us the following information: '{response.json()}'")
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception(f"Unable to reach endpoint at : {url}")
            raise ValidationError("UPayments : Could not establish the connection to the API.")
        response = response.json()
        if 'status' in response and response.get('status') == 'errors':
            if response.get('error_msg') and response.get('error_code'):
                raise ValidationError(f"UPayments : {response.get('error_msg')}")
            else:
                raise UserError(_("UPayments unreachable. Try again later or contact support."))
        parsed_url = urlparse(response['data']['link'])
        query_params = parse_qs(parsed_url.query)
        session_id = query_params.get('session_id', [None])[0]
        values = {
            'status': response['status'],
            'message': response['message'],
            'form_url': response['data']['link'],
            'sess_id': session_id,
        }
        return values

    def _get_default_payment_method_id(self, code):
        self.ensure_one()
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'upayments':
            return default_codes
        return self.env.ref('odoo_upayments.account_payment_method_upayments').id

    def _compute_feature_support_fields(self):
        """ It is update or set payment provider feature """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'upayments').update({
            'support_refund': 'partial',
        })

    def _upayments_get_api_url(self):
        """ Return the API URL according to the state """
        self.ensure_one()
        if self.state == 'enabled':
            return 'https://uapi.upayments.com/api/v1/charge'
        else:
            return 'https://sandboxapi.upayments.com/api/v1/charge'

    def get_all_payment_method(self):
        self.ensure_one()
        if self.state == 'enabled':
            url = 'https://uapi.upayments.com/api/v1/check-payment-button-status'
        else:
            url = 'https://sandboxapi.upayments.com/api/v1/check-payment-button-status'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.upay_application_key}',
        }
        try:
            with requests.Session() as session:
                response = session.get(url, headers=headers, timeout=10)
                if 'status' not in response.json():
                    raise ValidationError(_(response.json().get('message')))
        except (HTTPError, ConnectionError, Timeout) as e:
            _logger.exception(f"Failed to make API request to {url}")
            raise ValidationError(f"UPayments: Failed to make API request :: {e}")
        return response.json()

    def get_image_payment_method(self, key):
        image_path = f'odoo_upayments/static/description/method_icons/{key}.png'
        full_image_path = tools.file_open(image_path)
        try:
            with open(full_image_path.name, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read())
        except FileNotFoundError:
            raise UserError(f"Image file not found: {full_image_path.name}")
        if image_data:
            return image_data

    def update_payment_provider_method(self):
        u_pm_id = self.env['payment.method'].sudo().search(
            [('code', '=', 'upayments'), '|', ('active', '=', True), ('active', '=', False)])
        provider_id = self.env['payment.provider'].sudo().search([('code', '=', 'upayments')], limit=1)
        if not provider_id.api_type:
            return
        if provider_id:
            for rec in provider_id.payment_method_ids:
                rec.active = False
        if provider_id.api_type == 'white_label' and provider_id.code == 'upayments':
            u_pm_id.active = False
            result = provider_id.sudo().get_all_payment_method()
            if result.get('status'):
                total_method = result['data']['payButtons']
                if total_method:
                    for index, key in enumerate(total_method):
                        if total_method[key]:
                            pm = self.env['payment.method'].sudo().search(
                                [('is_upayment_method', '=', True),
                                 ('code', '=', key), '|',
                                 ('active', '=', True),
                                 ('active', '=', False)])
                            if pm:
                                pm.active = True
                            else:
                                vals = {
                                    'name': key.replace('_', ' ').title(),
                                    'code': key,
                                    'is_upayment_method': True,
                                    'support_tokenization': False,
                                    'support_express_checkout': True,
                                    'image': self.get_image_payment_method(key),
                                    'support_refund': 'partial',
                                    'provider_ids': [(4, provider_id.id)]
                                }
                                if key == 'credit_card':
                                    vals.update({'support_tokenization': True})
                                self.env['payment.method'].sudo().create(vals)
        else:
            if provider_id.api_type == 'non_white_label' and provider_id.code == 'upayments':
                # here i am calling get_all_payment_method only for check api key
                self.get_all_payment_method()
                u_pm_id.active = True
