# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TalyController(http.Controller):

    # ── Customer Return (Redirect) ─────────────────────────────────────────

    @http.route(
        '/payment/taly/return',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def taly_return(self, **kwargs):
        """
        Taly redirects customer here after checkout.
        Query params may include: status, merchantOrderId, orderToken, etc.
        """
        _logger.info("Taly return callback: %s", kwargs)

        reference = (
            kwargs.get('merchantOrderId')
            or kwargs.get('reference')
            or kwargs.get('order_reference')
        )
        status = kwargs.get('orderStatus') or kwargs.get('status') or 'PENDING'
        order_token = kwargs.get('orderToken') or kwargs.get('order_token')

        if reference:
            try:
                tx = request.env['payment.transaction'].sudo().search([
                    ('reference', '=', reference),
                    ('provider_code', '=', 'taly'),
                ], limit=1)
                if tx:
                    tx._process_notification_data({
                        'orderStatus': status.upper(),
                        'merchantOrderId': reference,
                        'orderToken': order_token,
                        **kwargs,
                    })
            except Exception as e:
                _logger.error("Taly return: error processing tx %s: %s", reference, e)

        return request.redirect('/payment/status')

    # ── Webhook (Async Server Notification) ──────────────────────────────────

    @http.route(
        '/payment/taly/webhook',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def taly_webhook(self, **kwargs):
        """
        Taly sends async order status updates here.
        Payload keys: amount, orderToken, currency, orderStatus, merchantOrderId, orderDate
        """
        raw_body = request.httprequest.data
        _logger.info("Taly webhook received (raw): %s", raw_body[:500])

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as e:
            _logger.error("Taly webhook: invalid JSON: %s", e)
            return request.make_response('invalid json', status=400)

        # ── Signature verification ─────────────────────────────────────────
        provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'taly'),
            ('state', 'in', ['enabled', 'test']),
        ], limit=1)

        if provider and provider.taly_webhook_secret:
            sig_header = request.httprequest.headers.get('Taly-Signature', '')
            if sig_header:
                # Taly's HMAC-SHA256: sort keys ascending, concatenate values with '&', remove leading '&'
                sorted_keys = sorted(data.keys())
                values_str = '&'.join(str(data[k]) for k in sorted_keys)
                if values_str.startswith('&'):
                    values_str = values_str[1:]
                expected_sig = hmac.new(
                    provider.taly_webhook_secret.encode('utf-8'),
                    values_str.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(sig_header, expected_sig):
                    _logger.warning("Taly webhook: signature mismatch! Rejecting.")
                    provider._taly_log(
                        'webhook_verify', 'error',
                        f"Signature mismatch. Got: {sig_header}, Expected: {expected_sig}"
                    )
                    return request.make_response('invalid signature', status=403)
                else:
                    _logger.info("Taly webhook: signature verified ✓")

        # ── Process transaction ────────────────────────────────────────────
        try:
            tx = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'taly', data
            )
            tx._process_notification_data(data)
            _logger.info("Taly webhook: processed tx %s → %s", tx.reference, data.get('orderStatus'))
            return request.make_response(
                json.dumps({'status': 'ok', 'reference': tx.reference}),
                headers={'Content-Type': 'application/json'},
            )
        except Exception as e:
            _logger.error("Taly webhook: failed to process: %s", e)
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers={'Content-Type': 'application/json'},
                status=422,
            )

    # ── On-Site Messaging: Installment Calculator API ─────────────────────

    @http.route(
        '/taly/widget/price',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def taly_widget_price(self, price=0, **kwargs):
        """
        Returns installment breakdown for a given price.
        Called from the product page JS widget.
        """
        provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'taly'),
            ('state', 'in', ['enabled', 'test']),
        ], limit=1)

        if not provider:
            return {'error': 'Taly not configured'}

        try:
            price = float(price)
        except (TypeError, ValueError):
            return {'error': 'Invalid price'}

        # Basic local calculation (before calling Taly's banner API)
        inst_type = int(provider.taly_installment_type or 3)
        down_pct = 1 / inst_type
        down_payment = round(price * down_pct, 3)
        remaining = round(price - down_payment, 3)
        remaining_per_installment = round(remaining / (inst_type - 1), 3) if inst_type > 1 else 0

        return {
            'price': price,
            'installment_type': inst_type,
            'down_payment': down_payment,
            'remaining': remaining,
            'remaining_per_installment': remaining_per_installment,
            'lang': provider.taly_widget_lang,
            'widget_url': (
                f"https://promo.taly.io/installment-widget"
                f"?price={price}&installmenttype={inst_type}"
                f"&lang={provider.taly_widget_lang}"
            ),
        }

    # ── Dashboard: JSON stats for backend chart ───────────────────────────

    @http.route(
        '/taly/dashboard/stats',
        type='json',
        auth='user',
        methods=['POST'],
    )
    def taly_dashboard_stats(self, provider_id=None, period='30', **kwargs):
        """Returns chart data for the Taly dashboard."""
        domain = [('provider_code', '=', 'taly')]
        if provider_id:
            domain.append(('provider_id', '=', int(provider_id)))

        txs = request.env['payment.transaction'].sudo().search(domain, order='create_date asc')

        from collections import defaultdict
        daily = defaultdict(lambda: {'count': 0, 'amount': 0.0, 'done': 0, 'cancel': 0})

        for tx in txs:
            day = tx.create_date.strftime('%Y-%m-%d') if tx.create_date else 'unknown'
            daily[day]['count'] += 1
            daily[day]['amount'] += tx.amount
            if tx.state == 'done':
                daily[day]['done'] += 1
            elif tx.state == 'cancel':
                daily[day]['cancel'] += 1

        return {
            'labels': list(daily.keys()),
            'counts': [v['count'] for v in daily.values()],
            'amounts': [round(v['amount'], 2) for v in daily.values()],
            'done': [v['done'] for v in daily.values()],
            'cancel': [v['cancel'] for v in daily.values()],
            'total_txs': len(txs),
            'total_done': len(txs.filtered(lambda t: t.state == 'done')),
            'total_amount': round(sum(txs.filtered(lambda t: t.state == 'done').mapped('amount')), 3),
        }
