# -*- coding: utf-8 -*-

import pprint
import logging
import werkzeug
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UpaymentsController(http.Controller):
    notificationUrl = '/notification/info'
    _success_url = '/redirect/success'
    _error_url = '/redirect/error'

    @http.route(notificationUrl, type="http", website=True, auth="public", csrf=False)
    def _upayments_redirect(self, **kw):
        _logger.info(f"UPayment KNet redirect payment link URL: {pprint.pformat(kw)}")
        if kw.get('upay_payment_link_url'):
            return werkzeug.utils.redirect(kw['upay_payment_link_url'])
        else:
            return werkzeug.utils.redirect('/payment/status')

    @http.route([_success_url, _error_url], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def upayments_return_from_checkout(self, **raw_data):
        """ Process the notification data sent by UPayments after redirection """
        _logger.info(f"Handling redirection from UPayments with data:\n{pprint.pformat(raw_data)}")
        try:
            request.env['payment.transaction'].sudo()._handle_notification_data('upayments', raw_data)
        except ValidationError:
            _logger.exception("Unable to handle the notification data ,skipping to acknowledge.")
        return request.redirect('/payment/status')
