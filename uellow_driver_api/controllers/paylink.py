# -*- coding: utf-8 -*-
"""Payment link for COD orders — /api/driver/v1/orders/<id>/payment-link*

Mirrors /delivery-portal/get-payment-link EXACTLY:
  1. UPayments KNET (preferred)
  2. Odoo /payment/pay (fallback)

Same sale.order field writes (pay_link_status, pay_link_url,
pay_link_sent_by, pay_link_sent_date, pay_link_provider) so the audit
trail stays unified with the portal.
"""
import logging

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
    fmt_price,
)


_logger = logging.getLogger(__name__)


def _generate(order, provider_pref='upayments'):
    """Returns (link, provider) tuple. Tries UPayments first, falls
    back to Odoo built-in payment link."""
    base_url = request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', 'https://www.uellow.com')
    if provider_pref == 'upayments':
        try:
            import requests as req_lib
            upay = request.env['payment.provider'].sudo().search(
                [('code', '=', 'upayments'), ('state', '=', 'enabled')], limit=1)
            key = getattr(upay, 'upay_application_key', '') if upay else ''
            if key:
                payload = {
                    'order': {
                        'id': order.name,
                        'reference': order.name,
                        'description': f'Payment for order {order.name}',
                        'currency': 'KWD',
                        'amount': round(order.amount_total, 3),
                    },
                    'products': [{
                        'name': f'Order {order.name}',
                        'description': f'Payment for {order.name}',
                        'price': round(order.amount_total, 3),
                        'quantity': 1,
                    }],
                    'returnUrl': f'{base_url}/payment/upayments/return',
                    'cancelUrl': f'{base_url}/payment/upayments/cancel',
                    'notificationUrl': f'{base_url}/payment/upayments/webhook',
                    'customerExtraData': str(order.id),
                    'language': 'ar',
                }
                resp = req_lib.post(
                    'https://api.upayments.com/api/v1/charge',
                    json=payload,
                    headers={'Authorization': f'Bearer {key}',
                             'Content-Type': 'application/json'},
                    timeout=15)
                data = resp.json()
                link = (data.get('data') or {}).get('link') or \
                       (data.get('data') or {}).get('paymentLink')
                if link:
                    return link, 'UPayments'
        except Exception as exc:
            _logger.warning('UPayments err: %s', exc)
    # Fallback: Odoo native /payment/pay
    try:
        from odoo.addons.payment import utils as payment_utils
        access_token = payment_utils.generate_access_token(
            order.partner_id.id, order.amount_total, order.currency_id.id)
        link = (
            f'{base_url}/payment/pay'
            f'?amount={order.amount_total}'
            f'&currency_id={order.currency_id.id}'
            f'&partner_id={order.partner_id.id}'
            f'&sale_order_id={order.id}'
            f'&access_token={access_token}'
        )
        return link, 'Odoo'
    except Exception as exc:
        _logger.error('Odoo payment-link err: %s', exc)
        return None, None


class DriverPaylinkAPI(http.Controller):

    @http.route('/api/driver/v1/orders/<int:order_id>/payment-link',
                type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def generate(self, order_id, **kw):
        driver = current_driver()
        if not driver.can_send_payment_link:
            return fail('FORBIDDEN',
                        'Driver is not allowed to send payment links', 403)
        p = get_payload()
        provider_pref = (p.get('provider') or 'upayments').lower()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return fail('NOT_FOUND', 'Order not found', 404)
        link, provider = _generate(order, provider_pref=provider_pref)
        if not link:
            return fail('GEN_FAILED', 'Could not generate payment link', 500)
        order.sudo().write({
            'pay_link_status':    'sent',
            'pay_link_url':       link,
            'pay_link_sent_by':   driver.portal_user_id.id or False,
            'pay_link_sent_date': fields.Datetime.now(),
            'pay_link_provider':  provider,
        })
        order.message_post(body=f'💳 Payment link generated ({provider}) by {driver.name}: {link}')
        return ok({
            'link': link,
            'provider': provider,
            'amount': fmt_price(order.amount_total, order.currency_id),
            'order_name': order.name,
            'customer': {
                'name':  order.partner_id.name,
                'phone': order.partner_id.mobile or order.partner_id.phone or '',
            },
        })

    @http.route('/api/driver/v1/orders/<int:order_id>/payment-link/status',
                type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def status(self, order_id, **kw):
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return fail('NOT_FOUND', 'Order not found', 404)
        last_tx = order.transaction_ids.filtered(
            lambda t: t.state in ('done', 'authorized'))[-1:]
        is_paid = bool(last_tx) or order.invoice_status == 'invoiced'
        return ok({
            'pay_link_status': getattr(order, 'pay_link_status', '') or 'none',
            'is_paid': is_paid,
            'paid_amount': fmt_price(
                last_tx.amount if last_tx else 0, order.currency_id),
            'provider': getattr(order, 'pay_link_provider', '') or '',
            'url': getattr(order, 'pay_link_url', '') or '',
        })

    @http.route('/api/driver/v1/orders/<int:order_id>/payment-link/share',
                type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def share(self, order_id, **kw):
        """Record that the driver shared the link via a specific channel
        (whatsapp/sms/clipboard/qr). The actual handoff happens in the
        app via deep links; the server just logs it."""
        p = get_payload()
        channel = (p.get('channel') or '').strip()
        if channel not in ('whatsapp', 'sms', 'clipboard', 'qr'):
            return fail('BAD_CHANNEL', 'channel must be whatsapp|sms|clipboard|qr')
        driver = current_driver()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return fail('NOT_FOUND', 'Order not found', 404)
        emoji = {'whatsapp': '💬', 'sms': '✉️',
                 'clipboard': '📋', 'qr': '🟫'}[channel]
        order.message_post(
            body=f'{emoji} Payment link shared via {channel} by {driver.name}')
        return ok({'logged': True, 'channel': channel})

    @http.route('/api/driver/v1/orders/<int:order_id>/payment-link/cancel',
                type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cancel(self, order_id, **kw):
        driver = current_driver()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return fail('NOT_FOUND', 'Order not found', 404)
        if 'pay_link_status' in order._fields:
            order.sudo().write({'pay_link_status': 'cancelled'})
        order.message_post(body=f'✕ Payment link cancelled by {driver.name}')
        return ok({'cancelled': True})
