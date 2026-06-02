# -*- coding: utf-8 -*-
"""Bearer-token session for the Driver mobile app.

Mirrors the design of `mobile.session` from uellow_mobile_manager but is
intentionally a separate table so a bug in customer auth can't take down
driver auth (and vice versa). Tokens are 60+ chars of url-safe random,
stored as sha256 — plaintext token only leaves the system once, in the
login response.
"""
import hashlib
import secrets

from odoo import fields, models, api


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class DriverSession(models.Model):
    _name = 'driver.session'
    _description = 'Driver App Session'
    _order = 'id desc'

    driver_id = fields.Many2one(
        'delivery.driver', required=True, ondelete='cascade', index=True,
    )
    user_id = fields.Many2one(
        'res.users', required=True, ondelete='cascade',
        help='The portal user behind this driver — used for permissions.',
    )
    token_hash = fields.Char(required=True, index=True)
    device_id = fields.Char(index=True, help='Stable per-install identifier')
    platform = fields.Selection([
        ('android', 'Android'),
        ('ios',     'iOS'),
        ('web',     'Web'),
    ], default='android')
    app_version = fields.Char()
    push_token = fields.Char(index=True,
        help='FCM token for push notifications')
    last_seen = fields.Datetime(default=fields.Datetime.now)
    last_ip = fields.Char()
    is_revoked = fields.Boolean(default=False)

    @api.model
    def issue(self, driver, device_id='', platform='android',
              app_version='', ip='', push_token=''):
        """Create a fresh session for the given delivery.driver.
        Returns (plaintext_token, session_record). The plaintext is NEVER
        stored — only its sha256."""
        user = driver.portal_user_id
        if not user:
            from odoo.exceptions import UserError
            from odoo import _
            raise UserError(_('Driver has no portal user yet.'))
        token = secrets.token_urlsafe(48)
        sess = self.sudo().create({
            'driver_id': driver.id,
            'user_id':   user.id,
            'token_hash': _hash(token),
            'device_id': device_id or '',
            'platform':  platform or 'android',
            'app_version': app_version or '',
            'last_ip':   ip or '',
            'push_token': push_token or '',
        })
        return token, sess

    @api.model
    def find_by_token(self, token):
        if not token:
            return self.browse()
        return self.sudo().search([
            ('token_hash', '=', _hash(token)),
            ('is_revoked', '=', False),
        ], limit=1)

    def touch(self, ip=''):
        for s in self:
            s.sudo().write({
                'last_seen': fields.Datetime.now(),
                'last_ip':   ip or s.last_ip,
            })

    def revoke(self):
        self.sudo().write({'is_revoked': True})
