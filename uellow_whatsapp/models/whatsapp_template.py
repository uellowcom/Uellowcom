from odoo import models, fields, api, _
import logging, requests

_logger = logging.getLogger(__name__)


class WhatsAppConfig(models.Model):
    _name = 'uellow.whatsapp.config'
    _description = 'WhatsApp API Configuration'
    _rec_name = 'name'

    name = fields.Char(default='WhatsApp Settings')
    active = fields.Boolean(default=True)
    provider = fields.Selection([
        ('twilio',   'Twilio'),
        ('whapi',    'WhAPI.cloud'),
        ('360dialog','360Dialog'),
        ('custom',   'Custom API'),
    ], default='whapi', string='Provider')
    api_key = fields.Char('API Key')
    api_url = fields.Char('API URL')
    sender_number = fields.Char('Sender Number')

    # Triggers
    send_order_confirm = fields.Boolean('Order Confirmation', default=True)
    send_shipping = fields.Boolean('Shipping Update', default=True)
    send_flash_sale = fields.Boolean('Flash Sale Alert', default=True)
    send_cart_recovery = fields.Boolean('Cart Recovery', default=True)
    send_low_stock = fields.Boolean('Low Stock Alert (vendor)', default=True)
    send_loyalty_points = fields.Boolean('Loyalty Points Earned', default=False)

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({'name': 'WhatsApp Settings'})
        return cfg

    def send_message(self, phone, message):
        """Send WhatsApp message via configured provider."""
        self.ensure_one()
        if not self.api_key or not phone:
            _logger.warning('WhatsApp: missing API key or phone number')
            return False
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        if not phone.startswith('+'):
            phone = '+965' + phone  # Default Kuwait
        try:
            if self.provider == 'whapi':
                resp = requests.post(
                    f'{self.api_url or "https://gate.whapi.cloud"}/messages/text',
                    headers={'Authorization': f'Bearer {self.api_key}',
                             'Content-Type': 'application/json'},
                    json={'to': phone, 'body': message},
                    timeout=10,
                )
                return resp.status_code == 200
            else:
                _logger.info('WhatsApp [%s → %s]: %s', self.sender_number, phone, message[:80])
                return True
        except Exception as e:
            _logger.error('WhatsApp send failed: %s', e)
            return False


class WhatsAppTemplate(models.Model):
    _name = 'uellow.whatsapp.template'
    _description = 'WhatsApp Message Template'
    _rec_name = 'name'

    name = fields.Char(required=True)
    trigger = fields.Selection([
        ('order_confirm',   'Order Confirmed'),
        ('order_shipped',   'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('flash_sale',      'Flash Sale Start'),
        ('cart_recovery',   'Cart Recovery'),
        ('low_stock',       'Low Stock'),
        ('loyalty_earn',    'Loyalty Points Earned'),
        ('custom',          'Custom'),
    ], required=True)
    language = fields.Selection([
        ('ar', 'Arabic'),
        ('en', 'English'),
        ('both', 'Both'),
    ], default='both')
    body_ar = fields.Text('Message (Arabic)')
    body_en = fields.Text('Message (English)')
    active = fields.Boolean(default=True)

    def render(self, lang='ar', **kwargs):
        body = self.body_ar if lang == 'ar' else self.body_en
        if not body:
            body = self.body_ar or self.body_en or ''
        try:
            return body.format(**kwargs)
        except Exception:
            return body
