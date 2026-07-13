"""Public UPayments return + webhook endpoints.

Flow: the mobile checkout creates a charge (sale.order._upayments_create_charge)
and opens the returned hosted link in a webview. After payment UPayments
redirects the browser to /payments/upayments/return (the app auto-closes on
this URL) and POSTs a notification to /payments/upayments/webhook which marks
the order paid.
"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_OK_RESULTS = {'CAPTURED', 'SUCCESS', 'SUCCESSFUL', 'DONE', 'AUTHORIZED'}


def _page(title, msg):
    html = (
        "<!doctype html><html><head><meta name='viewport' "
        "content='width=device-width,initial-scale=1'><title>%s</title></head>"
        "<body style='font-family:system-ui,sans-serif;text-align:center;"
        "padding:60px 24px;color:#412402'><h2>%s</h2><p style='color:#777'>%s</p>"
        "</body></html>" % (title, title, msg))
    return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])


class UPaymentsController(http.Controller):

    @http.route('/payments/upayments/return', type='http', auth='public',
                csrf=False, methods=['GET', 'POST'])
    def upay_return(self, **kw):
        # The app's webview detects this path and closes. The webhook is the
        # primary capture signal but sometimes never fires (S06360) — so the
        # return flow now ACTIVELY verifies the charge against the UPayments
        # status API and captures the order if paid. `oid` is the order id we
        # appended to our own returnUrl, so this lookup is reliable.
        oid = kw.get('oid') or kw.get('order_id') or kw.get('ref')
        if oid:
            try:
                order = request.env['sale.order'].sudo().browse(int(oid))
                if order.exists() and hasattr(
                        order, '_upayments_verify_status'):
                    order._upayments_verify_status()
            except Exception:
                _logger.exception(
                    'UPayments return-verify failed (oid=%s)', oid)
        return _page('Payment complete', 'You can return to the app.')

    @http.route('/payments/upayments/cancel', type='http', auth='public',
                csrf=False, methods=['GET', 'POST'])
    def upay_cancel(self, **kw):
        return _page('Payment cancelled', 'You can return to the app and try again.')

    @http.route('/payments/upayments/webhook', type='http', auth='public',
                csrf=False, methods=['POST', 'GET'])
    def upay_webhook(self, **kw):
        data = dict(kw or {})
        try:
            raw = request.httprequest.get_data()
            if raw and raw.strip().startswith(b'{'):
                data.update(json.loads(raw))
        except Exception:
            pass
        result = str(data.get('result') or data.get('status') or '').upper()
        ref = data.get('ref') or data.get('requested_order_id') or data.get('order_id')
        track = data.get('track_id') or data.get('trackId')
        payment_id = data.get('payment_id') or data.get('tran_id')
        order = None
        if ref:
            try:
                order = request.env['sale.order'].sudo().browse(int(ref))
                if not order.exists():
                    order = None
            except Exception:
                order = None
        if order is None and track:
            order = request.env['sale.order'].sudo().search(
                [('upayments_track_id', '=', track)], limit=1) or None
        if order is not None and order.exists():
            try:
                if track and not order.upayments_track_id:
                    order.sudo().write({'upayments_track_id': track})
                if result in _OK_RESULTS:
                    order._upayments_mark_paid(track_id=track, payment_id=payment_id)
                elif not result and hasattr(order, '_upayments_verify_status'):
                    # Webhook fired without a clear result field — confirm
                    # against the status API rather than silently ignoring it.
                    order._upayments_verify_status()
            except Exception:
                _logger.exception('UPayments webhook processing failed')
        else:
            _logger.warning('UPayments webhook: no matching order (ref=%s track=%s)', ref, track)
        return request.make_json_response({'status': True})
