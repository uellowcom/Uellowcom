from odoo import models, fields, api
import secrets
import hashlib
from datetime import timedelta


class DeliveryToken(models.Model):
    """JWT-like token for delivery boy authentication."""
    _name = 'uellow.delivery.token'
    _description = 'Delivery Boy Auth Token'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    token_hash = fields.Char('Token Hash', index=True)
    expires_at = fields.Datetime('Expires At')
    active = fields.Boolean(default=True)
    device_info = fields.Char('Device Info')

    @api.model
    def generate_token(self, user):
        """Generate a new token for a delivery user."""
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires_at = fields.Datetime.now() + timedelta(days=30)
        # Deactivate old tokens
        self.search([('user_id', '=', user.id), ('active', '=', True)]).write({'active': False})
        self.create({
            'user_id': user.id,
            'token_hash': token_hash,
            'expires_at': expires_at,
        })
        return raw

    @api.model
    def validate_token(self, raw_token):
        """Validate token and return user."""
        import hashlib
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = self.search([
            ('token_hash', '=', token_hash),
            ('active', '=', True),
            ('expires_at', '>', fields.Datetime.now()),
        ], limit=1)
        return token.user_id if token else False
