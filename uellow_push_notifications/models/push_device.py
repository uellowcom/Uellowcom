from odoo import models, fields


class PushDevice(models.Model):
    """FCM device token per user."""
    _name = 'uellow.push.device'
    _description = 'Push Notification Device'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    fcm_token = fields.Char('FCM Token', required=True, index=True)
    platform = fields.Selection([('ios','iOS'),('android','Android'),('web','Web')], default='android')
    active = fields.Boolean(default=True)
    last_seen = fields.Datetime('Last Seen', default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_token', 'UNIQUE(fcm_token)', 'Token already registered.'),
    ]
