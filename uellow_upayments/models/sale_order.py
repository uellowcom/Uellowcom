import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

_logger = logging.getLogger(__name__)

_DEFAULT_BASE = 'https://sandboxapi.upayments.com/api/v1'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    upayments_link = fields.Char('UPayments link', readonly=True, copy=False)
    upayments_track_id = fields.Char('UPayments track id', readonly=True, copy=False)
    upayments_paid = fields.Boolean('Paid via UPayments', readonly=True, copy=False)

    def _upayments_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        base = (ICP.get_param('uellow_upayments.base_url') or _DEFAULT_BASE).rstrip('/')
        token = (ICP.get_param('uellow_upayments.token') or '').strip()
        return base, token

    def _upayments_create_charge(self, return_url, cancel_url, notify_url,
                                 lang='en', gateway=None):
        """Create a UPayments charge and return the hosted payment link."""
        self.ensure_one()
        if requests is None:
            raise UserError(_('The Python "requests" library is missing.'))
        base, token = self._upayments_config()
        if not token:
            raise UserError(_('UPayments is not configured (missing API token).'))
        p = self.partner_id
        lines = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_reward_line)
        payload = {
            'order': {
                'id': (self.name or str(self.id))[:40],
                'description': ('Order %s' % (self.name or self.id))[:500],
                'currency': (self.currency_id.name or 'KWD')[:3],
                'amount': round(self.amount_total or 0.0, 3),
            },
            'language': 'ar' if (lang or 'en').startswith('ar') else 'en',
            'reference': {'id': str(self.id)[:35]},
            'returnUrl': (return_url or '')[:250],
            'cancelUrl': (cancel_url or '')[:250],
            'notificationUrl': (notify_url or '')[:250],
        }
        # Customer (optional) — only include a mobile that looks valid
        # (UPayments rejects malformed mobiles), and only attach customer at all
        # when we have something meaningful.
        customer = {
            'uniqueId': str(p.id)[:50],
            'name': (p.name or 'Customer')[:50],
            'email': (p.email or 'guest@uellow.com')[:50],
        }
        raw_mobile = (p.mobile or p.phone or '').strip()
        digits = ''.join(ch for ch in raw_mobile if ch.isdigit())
        if len(digits) >= 8:
            customer['mobile'] = ('+' + digits)[:15]
        payload['customer'] = customer
        # Products are OPTIONAL — only send well-formed line items (name +
        # positive price + quantity). A malformed/zero-price line makes
        # UPayments reject the whole charge ("check product name/quantity/
        # price"), so skip anything that doesn't qualify and omit the array
        # entirely if none qualify (the charge still runs on order.amount).
        products = []
        for l in lines:
            name = (l.product_id.display_name or '').strip()
            price = round(l.price_unit or 0.0, 3)
            qty = int(l.product_uom_qty or 0)
            if name and price > 0 and qty > 0:
                products.append({'name': name[:255], 'description': name[:255],
                                 'price': price, 'quantity': qty})
        if products:
            payload['products'] = products[:50]
        if gateway:
            payload['paymentGateway'] = {'src': gateway}
        try:
            r = requests.post(
                base + '/charge',
                headers={'Authorization': 'Bearer %s' % token,
                         'Content-Type': 'application/json',
                         'Accept': 'application/json'},
                json=payload, timeout=30)
            data = r.json()
        except Exception as e:
            _logger.exception('UPayments charge request failed')
            raise UserError(_('Could not reach UPayments: %s') % e)
        if not data.get('status'):
            raise UserError(data.get('message') or _('UPayments rejected the charge.'))
        link = (data.get('data') or {}).get('link')
        if not link:
            raise UserError(_('UPayments did not return a payment link.'))
        self.sudo().write({'upayments_link': link})
        return link

    def _upayments_mark_paid(self, track_id=None, payment_id=None):
        """Flag the order paid + confirm it (called from the webhook on
        CAPTURED). Online orders stay a draft cart at checkout, so a successful
        payment is what actually confirms them."""
        self.ensure_one()
        vals = {'upayments_paid': True}
        if track_id:
            vals['upayments_track_id'] = track_id
        self.sudo().write(vals)
        try:
            if self.state in ('draft', 'sent'):
                self.sudo().action_confirm()
        except Exception:
            _logger.exception('UPayments: confirm-on-capture failed for %s', self.id)
        try:
            self.sudo().message_post(body=_(
                'UPayments payment captured (track: %s, payment_id: %s).')
                % (track_id or '-', payment_id or '-'))
        except Exception:
            pass
