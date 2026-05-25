from odoo import models, fields, api


class PushConfig(models.Model):
    _name = 'uellow.push.config'
    _description = 'Push Notification Config'

    name = fields.Char(default='Push Notification Settings')
    active = fields.Boolean(default=True)
    fcm_server_key = fields.Char('FCM Server Key')
    fcm_project_id = fields.Char('FCM Project ID')

    send_order_confirm = fields.Boolean('Order Confirmed', default=True)
    send_order_shipped = fields.Boolean('Order Shipped', default=True)
    send_flash_sale = fields.Boolean('Flash Sale Start', default=True)
    send_loyalty_milestone = fields.Boolean('Loyalty Milestone', default=True)
    send_vendor_new_order = fields.Boolean('Vendor: New Order', default=True)
    send_vendor_low_stock = fields.Boolean('Vendor: Low Stock', default=True)

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
        return cfg

    def send(self, tokens, title, body, data=None):
        """Send FCM push notification to list of tokens."""
        if not self.fcm_server_key or not tokens:
            return False
        import requests
        payload = {
            'registration_ids': tokens,
            'notification': {'title': title, 'body': body},
            'data': data or {},
        }
        try:
            resp = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                headers={'Authorization': f'key={self.fcm_server_key}',
                         'Content-Type': 'application/json'},
                json=payload, timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
