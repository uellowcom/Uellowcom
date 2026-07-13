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
        # No gateway link → the charge could not be created. Don't dump the
        # customer on the bare /payment/status "payment not found" page; send
        # them back to checkout so they can retry / pick another method.
        _logger.warning("UPayments: /notification/info hit without a payment link — back to checkout.")
        return werkzeug.utils.redirect('/shop/payment?upay_retry=1')

    @http.route([_success_url, _error_url], type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def upayments_return_from_checkout(self, **raw_data):
        """ Process the notification data sent by UPayments after redirection """
        _logger.info(f"Handling redirection from UPayments with data:\n{pprint.pformat(raw_data)}")
        try:
            request.env['payment.transaction'].sudo()._handle_notification_data('upayments', raw_data)
        except ValidationError:
            _logger.exception("Unable to handle the notification data ,skipping to acknowledge.")
        # Re-establish the monitored transaction in the session. The browser
        # returns here from an EXTERNAL domain (kpay.com.kw / upayments.com),
        # and a SameSite=Lax session cookie may be dropped on that cross-site
        # POST — losing __payment_monitored_tx_id__ and making /payment/status
        # render the generic "payment not found" page even though the payment
        # was processed. Recover the tx by its reference (always present in the
        # return data) and pin it back into the session.
        try:
            tx = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'upayments', raw_data)
            if tx:
                request.session['__payment_monitored_tx_id__'] = tx.id
        except Exception as e:
            _logger.warning("UPayments: could not recover tx on return: %s", e)
        return request.redirect('/payment/status')
