# -*- coding: utf-8 -*-
"""Bearer-token session for the Vendor mobile app.

Separate from mobile.session (customer) and driver.session (driver) —
isolated tables so an auth bug in one app cannot disable any other.
"""
import hashlib
import secrets

from odoo import fields, models, api


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class VendorSession(models.Model):
    _name = 'vendor.session'
    _description = 'Vendor App Session'
    _order = 'id desc'

    vendor_id = fields.Many2one('uellow.vendor', required=True,
        ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
    token_hash = fields.Char(required=True, index=True)
    device_id = fields.Char(index=True)
    platform = fields.Selection([
        ('android', 'Android'), ('ios', 'iOS'), ('web', 'Web'),
    ], default='android')
    app_version = fields.Char()
    push_token = fields.Char(index=True)
    last_seen = fields.Datetime(default=fields.Datetime.now)
    last_ip = fields.Char()
    is_revoked = fields.Boolean(default=False)

    @api.model
    def issue(self, vendor, device_id='', platform='android',
              app_version='', ip='', push_token=''):
        if not vendor.user_id:
            from odoo.exceptions import UserError
            from odoo import _
            raise UserError(_('Vendor has no portal user yet.'))
        token = secrets.token_urlsafe(48)
        sess = self.sudo().create({
            'vendor_id': vendor.id,
            'user_id': vendor.user_id.id,
            'token_hash': _hash(token),
            'device_id': device_id or '',
            'platform': platform or 'android',
            'app_version': app_version or '',
            'last_ip': ip or '',
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
            s.sudo().write({'last_seen': fields.Datetime.now(),
                            'last_ip': ip or s.last_ip})

    def revoke(self):
        self.sudo().write({'is_revoked': True})
