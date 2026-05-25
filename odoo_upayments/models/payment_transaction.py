# -*- coding: utf-8 -*-
import re
import logging
import requests
import pprint
from lxml import html
from werkzeug import urls
from odoo import _, models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.addons.odoo_upayments.controllers.main import UpaymentsController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    upayment_payment_ref = fields.Char(string='Payments Reference')
    upayment_payment_id = fields.Char(string='Payments ID')
    upayment_track_id = fields.Char(string='Payments Track ID')
    upayment_transaction_id = fields.Char(string='Payments Transaction ID')
    upayment_auth = fields.Char(string='Payments Auth')
    upayment_transaction_date = fields.Datetime('Transaction Date')
    upayment_receipt_id = fields.Char('Receipt ID')
    upayment_invoice_id = fields.Char('Invoice ID')
    upayment_payment_type = fields.Char('Payment Type')
    upayment_refund_order_id = fields.Char('Refund Order ID')
    upayment_requested_order_id = fields.Char('Request Order ID')
    upayment_result = fields.Char('Result')
    upayment_post_date = fields.Char('Post Date')
    upayment_verified = fields.Selection(
        [('success', 'Payment Success'), ('failed', 'Payment Failed')],
        string='Payment Verified',
    )
    refund_verified = fields.Selection(
        [('success', 'Refund Success'), ('failed', 'Refund Failed')],
        string='Refund Verified',
    )
    upayment_refundArn = fields.Char('RefundArn')
    total_paid_non_kwd = fields.Char('Total Paid In KWD')
    customer_id = fields.Char('Customer ID')

    def generate_customer_unique_token(self, partner_id):
        """ generate customer unique token """
        if partner_id:
            if self.provider_id.state == 'enabled':
                url = 'https://uapi.upayments.com/api/v1/create-customer-unique-token'
            else:
                url = 'https://sandboxapi.upayments.com/api/v1/create-customer-unique-token'
            customer_phone = str(partner_id.phone)
            phone = ''.join(re.findall(r'\d', customer_phone))
            if not phone:
                raise ValidationError(
                    _(f'Please provide phone number in partner and partner name is {partner_id.name}.'))
            payload = {"customerUniqueToken": phone}
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                'Authorization': f'Bearer {self.provider_id.upay_application_key}',
            }
            response = requests.post(url, headers=headers, params=payload)
            try:
                result = response.json()
                if 'status' in result and result.get('status'):
                    partner_id.sudo().update({'unique_token': result['data']['customerUniqueToken']})
                elif 'message' in result:
                    raise ValidationError(f"Please provide a unique phone number for: {partner_id.name}.")
                else:
                    raise ValidationError(_("Error generating or fetching the customer's unique token."))
            except ValueError:
                raise ValidationError(_('Invalid response from the server'))

    def get_payload_data(self):
        base_url = "https://www.uellow.com/"
        payload = {
            "order": {
                "id": self.reference,
                "reference": self.reference,
                "description": "",
                "currency": self.currency_id.name,
                "amount": self.amount
            },
            "language": "en",
            "reference": {"id": self.reference},
            "plugin": {"src": "odoo"},
            "customer": {
                "uniqueId": str(self.partner_id.id),
                "name": self.partner_id.name,
                "email": self.partner_id.email,
                "mobile": self.partner_id.phone,
            },
            "returnUrl": f"{base_url}redirect/success",
            "cancelUrl": f"{base_url}redirect/error",
            "notificationUrl": f"{base_url}notification/info",
        }
        return payload

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return UPayments-specific rendering values.
        Note: self.ensure_one() from `_get_processing_values`
        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of acquirer-specific rendering values
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'upayments':
            return res
        base_url = "https://www.uellow.com/"
        payload = self.get_payload_data()

        if self.provider_id.api_type == 'white_label':
            payment_method = self.payment_method_id.code
            if self.payment_method_id.code == 'samsung_pay':
                payment_method = 'samsung-pay'
            if self.payment_method_id.code == 'apple_pay':
                payment_method = 'apple-pay'
            if self.payment_method_id.code == 'google_pay':
                payment_method = 'google-pay'
            if self.payment_method_id.code == 'credit_card':
                payment_method = 'cc'
            payload.update({"paymentGateway": {"src": payment_method}})

        if self.tokenize:
            if self.partner_id and not self.partner_id.unique_token:
                self.generate_customer_unique_token(partner_id=self.partner_id)
            payload.update({
                "isSaveCard": True,
                "tokens": {"customerUniqueToken": self.partner_id.unique_token},
            })

        payment_link_data = self.provider_id._upayments_make_request(payload=payload)
        rendering_values = {
            'api_url': urls.url_join(base_url, UpaymentsController.notificationUrl),
            'upay_payment_link_url': payment_link_data['form_url'],
            'sess_id': payment_link_data['sess_id'],
        }
        return rendering_values

    def get_card_information(self):
        if self.provider_id.state == 'enabled':
            url = 'https://uapi.upayments.com/api/v1/retrieve-customer-cards'
        else:
            url = 'https://sandboxapi.upayments.com/api/v1/retrieve-customer-cards'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.provider_id.upay_application_key}',
        }
        params = {"customerUniqueToken": self.partner_id.unique_token}
        response = requests.post(url, params=params, headers=headers, timeout=10)
        return response.json()

    def _send_payment_request(self):
        """ This method call when payment cut off by save card of user """
        super()._send_payment_request()
        if self.provider_code not in (
                'upayments', 'knet', 'credit_card', 'samsung_pay', 'apple_pay', 'amex', 'google_pay'):
            return
        if not self.token_id:
            raise UserError("UPayments: " + _("The transaction is not linked to a token."))
        token_info = False
        result = self.get_card_information()
        if 'status' in result and result['status']:
            token_info = result['data']['customerCards'][0]['token']
        else:
            if 'errors' in result:
                raise ValidationError(_(result['message']))
        payload = self.get_payload_data()
        payload.update({
            "tokens": {'creditCard': token_info, },
            "paymentGateway": {"src": 'cc'}
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.provider_id.upay_application_key}',
        }
        if self.provider_id.state == 'enabled':
            url = 'https://uapi.upayments.com/api/v1/charge'
        else:
            url = 'https://sandboxapi.upayments.com/api/v1/charge'
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        _logger.info(f"Payment request response:\n{pprint.pformat(result)}")
        if result.get('status'):
            self._handle_notification_data(self.provider_code, result.get('data').get('transactionData'))
        else:
            raise ValidationError(_(result.get('message')))

    def _send_refund_request(self, amount_to_refund=None):
        """ This method call when user want to refund payment """
        if self.provider_code != 'upayments':
            return super()._send_refund_request(amount_to_refund=amount_to_refund)
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)

        refund_currency_id = self.env['res.currency'].sudo().search([('name', '=', 'KWD')], limit=1)
        if not refund_currency_id:
            raise ValidationError(_(f"Please active 'KWD' currency."))

        converted_amount = self.currency_id._convert(
            amount_to_refund,
            refund_currency_id,
            self.env.company,
            fields.Date.today()
        )

        if self.provider_id.state == 'enabled':
            url = 'https://uapi.upayments.com/api/v1/create-refund'
        else:
            url = 'https://sandboxapi.upayments.com/api/v1/create-refund'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.provider_id.upay_application_key}',
        }
        if not self.upayment_refund_order_id:
            raise ValidationError(_('Refund order id is not valid.'))
        payload = {
            "orderId": self.upayment_refund_order_id,
            "totalPrice": converted_amount,
            "customerFirstName": self.partner_id.name,
            "customerEmail": self.partner_email,
            "reference": str(self.upayment_payment_ref),
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        _logger.info(f"Refund request response:\n{pprint.pformat(result)}")
        if result['status']:
            refund_tx.upayment_requested_order_id = result['data']['orderId']
            refund_tx.upayment_refund_order_id = result['data']['refundOrderId']
            refund_tx.upayment_refundArn = result['data']['refundArn']
            refund_tx.source_transaction_id = self.id
            refund_tx.provider_reference = self.provider_id.code
            refund_tx._set_done()
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        else:
            raise ValidationError(_(result.get('message')))
        return refund_tx

    def _get_tx_from_notification_data(self, provider, notification_data):
        """ Find the transaction based on the feedback data.
        For an acquirer to handle transaction post-processing.
        return the transaction matching the data.
        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the acquirer
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_notification_data(provider, notification_data)
        if provider != 'upayments':
            return tx
        if 'reference' in notification_data:
            reference = notification_data.get('reference')
        else:
            reference = notification_data.get('requested_order_id')
        if not reference:
            raise ValidationError(f"UPayments: Received data with missing reference.")
        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'upayments')])
        if not tx:
            raise ValidationError(f"UPayments: No transaction found matching reference {reference}.")
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Mollie data.
        Note: self.ensure_one()
        :param dict notification_data: The feedback data sent by the provider
        :return: None
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'upayments':
            return
        vals = {
            'provider_reference': notification_data.get('order_id') if notification_data.get('order_id') else '',
            'upayment_payment_ref': notification_data.get('ref') if notification_data.get('ref') else '',
            'upayment_payment_id': notification_data.get('payment_id') if notification_data.get('payment_id') else '',
            'upayment_track_id': notification_data.get('track_id') if notification_data.get('track_id') else '',
            'upayment_auth': notification_data.get('auth') if notification_data.get('auth') else '',
            'upayment_post_date': notification_data.get('post_date') if notification_data.get('post_date') else '',
            'upayment_requested_order_id': notification_data.get('requested_order_id') if notification_data.get(
                'requested_order_id') else '',
            'upayment_refund_order_id': notification_data.get('refund_order_id') if notification_data.get(
                'refund_order_id') else '',
            'upayment_payment_type': notification_data.get('payment_type') if notification_data.get(
                'payment_type') else '',
            'upayment_invoice_id': notification_data.get('invoice_id') if notification_data.get('invoice_id') else '',
            'upayment_receipt_id': notification_data.get('receipt_id') if notification_data.get('receipt_id') else '',
            'upayment_transaction_id': notification_data.get('tran_id') if notification_data.get('tran_id') else '',
            'upayment_result': notification_data.get('result') if notification_data.get('result') else '',
            'upayment_transaction_date': notification_data.get('transaction_date') if notification_data.get(
                'transaction_date') else '',
        }
        status = notification_data.get('result')
        if not status:
            raise ValidationError("UPayments: Received data with missing payment state.")
        self.write(vals)
        if status == 'CAPTURED':
            self._set_done()
            if self.tokenize:
                self._upayment_tokenize_from_notification_data(notification_data)
        elif status == 'CANCELED':
            self._set_canceled()
        elif status in ['ERROR', 'NOT CAPTURED']:
            error_msg_html = self.provider_id.error_msg
            parsed_content = html.fromstring(error_msg_html).text_content()
            self._set_error(_(f"{parsed_content} : {status}"))
        else:
            _logger.info(
                f"Received data with invalid payment status ({status}) for transaction with reference {self.reference}")
            self._set_error(f"UPayments: Received invalid transaction status :: {status}.")

    def save_payment_card(self, fetch_card, notification_data):
        name = f"{fetch_card.get('brand')} [{fetch_card.get('number')}]"
        token_vals = {
            'payment_details': name,
            'card_number': fetch_card.get('number'),
            'token': fetch_card.get('token'),
            'provider_id': self.provider_id.id,
            'payment_method_id': self.payment_method_id.id,
            'partner_id': self.partner_id.id,
            'provider_ref': notification_data.get('ref'),
            'unique_token': self.partner_id.unique_token,
        }
        token = self.env['payment.token'].create(token_vals)
        self.write({
            'token_id': token.id,
            'tokenize': False,
        })
        _logger.info(
            f"Created token with id {token.id} for partner with id {self.partner_id.id} from "
            f"transaction with reference {self.reference}")

    def _upayment_tokenize_from_notification_data(self, notification_data):
        self.ensure_one()
        result = self.get_card_information()
        if 'errors' in result:
            raise ValidationError(_(result['message']))
        if 'status' in result and result['status']:
            fetch_card = result['data']['customerCards']
            if fetch_card:
                saved_card = self.env['payment.token'].search(
                    [('provider_id', '=', self.provider_id.id),
                     ('partner_id', '=', self.partner_id.id),
                     ('unique_token', '=', self.partner_id.unique_token)])
                for fc in fetch_card:
                    card_number = fc.get('number')
                    token = fc.get('token')
                    card_available = saved_card.filtered(lambda sc: sc.card_number == card_number and sc.token == token)
                    if not card_available:
                        self.save_payment_card(fetch_card=fc, notification_data=notification_data)

    def check_payment_status(self):
        if self.upayment_track_id:
            if self.provider_id.state == 'enabled':
                url = f'https://uapi.upayments.com/api/v1/get-payment-status/{self.upayment_track_id}'
            else:
                url = f'https://sandboxapi.upayments.com/api/v1/get-payment-status/{self.upayment_track_id}'
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.provider_id.upay_application_key}',
            }
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
            if result['status'] and result['data']['transaction']['result'] == 'CAPTURED':
                self.total_paid_non_kwd = result['data']['transaction']['total_paid_non_kwd']
                self.customer_id = result['data']['transaction']['customer_id']
                message = f"Payment Success Result 'CAPTURED'"
                self.upayment_verified = 'success'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {'message': message, 'type': 'success'}
                }
            else:
                self.upayment_verified = 'failed'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {'message': result['message'], 'type': 'danger'}
                }
        else:
            raise ValidationError(_('Track ID is not valid.'))

    def check_refund_status(self):
        if self.upayment_requested_order_id:
            if self.provider_id.state == 'enabled':
                url = f'https://uapi.upayments.com/api/v1/check-refund-status/{self.upayment_requested_order_id}'
            else:
                url = f'https://sandboxapi.upayments.com/api/v1/check-refund-status/{self.upayment_requested_order_id}'
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.provider_id.upay_application_key}',
            }
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
            if result['status']:
                self.refund_verified = 'success'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {'message': result['message'], 'type': 'success'}
                }
            else:
                self.refund_verified = 'failed'
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                    'params': {'message': result['message'], 'type': 'danger'}
                }
        else:
            raise ValidationError(_('Refund order ID is not valid.'))
# Debug patch - will be removed
import logging as _logging
_upay_logger = _logging.getLogger('uellow.upayments.debug')
