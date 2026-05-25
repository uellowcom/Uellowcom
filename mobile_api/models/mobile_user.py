# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Mobile-specific fields
    mobile_device_ids = fields.One2many('mobile.device', 'partner_id', string='Mobile Devices')
    mobile_last_login = fields.Datetime('Last Mobile Login')
    mobile_app_version = fields.Char('Mobile App Version')
    mobile_preferences = fields.Text('Mobile Preferences')
    mobile_notification_token = fields.Char('Firebase Notification Token')

    # Firebase authentication
    firebase_uid = fields.Char('Firebase UID', index=True)

    # Social login IDs
    google_id = fields.Char('Google ID')
    facebook_id = fields.Char('Facebook ID')
    apple_id = fields.Char('Apple ID')

    # Mobile verification
    mobile_verified = fields.Boolean('Mobile Verified', default=False)
    mobile_verification_code = fields.Char('Mobile Verification Code')
    mobile_verification_sent = fields.Datetime('Mobile Verification Sent')

    # Wallet
    wallet_balance = fields.Float('Wallet Balance', default=0.0)

    @api.model
    def create_mobile_user(self, vals):
        """Create user for mobile app"""
        vals.update({
            'is_company': False,
            'customer_rank': 1,
        })
        return self.create(vals)

    @api.model
    def find_or_create_by_firebase(self, firebase_uid, user_data):
        """Find or create user by Firebase UID"""
        partner = self.search([('firebase_uid', '=', firebase_uid)], limit=1)
        if not partner:
            vals = {
                'name': user_data.get('name', 'Mobile User'),
                'email': user_data.get('email'),
                'firebase_uid': firebase_uid,
                'mobile_verified': True,
                'is_company': False,
                'customer_rank': 1,
            }
            partner = self.create(vals)
        return partner

    @api.model
    def find_or_create_by_social(self, provider, social_id, user_data):
        """Find or create user by social login"""
        field_map = {
            'google': 'google_id',
            'facebook': 'facebook_id',
            'apple': 'apple_id'
        }

        if provider not in field_map:
            raise ValidationError(_('Invalid social provider'))

        field_name = field_map[provider]
        partner = self.search([(field_name, '=', social_id)], limit=1)

        if not partner:
            vals = {
                'name': user_data.get('name', f'{provider.title()} User'),
                'email': user_data.get('email'),
                field_name: social_id,
                'mobile_verified': True,
                'is_company': False,
                'customer_rank': 1,
            }
            partner = self.create(vals)

        return partner

    def update_mobile_preferences(self, preferences):
        """Update mobile app preferences"""
        self.ensure_one()
        current_prefs = json.loads(self.mobile_preferences or '{}')
        current_prefs.update(preferences)
        self.mobile_preferences = json.dumps(current_prefs)

    def get_mobile_preferences(self):
        """Get mobile app preferences"""
        self.ensure_one()
        return json.loads(self.mobile_preferences or '{}')

    def update_notification_token(self, token):
        """Update Firebase notification token"""
        self.ensure_one()
        self.mobile_notification_token = token

    def add_wallet_balance(self, amount, description=""):
        """Add amount to wallet balance"""
        self.ensure_one()
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))
        self.wallet_balance += amount
        self.env['mobile.wallet.transaction'].create({
            'partner_id': self.id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': description,
            'reference': self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/',
        })

    def deduct_wallet_balance(self, amount, description=""):
        """Deduct amount from wallet balance"""
        self.ensure_one()
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))
        if self.wallet_balance < amount:
            raise ValidationError(_('Insufficient wallet balance'))
        self.wallet_balance -= amount
        self.env['mobile.wallet.transaction'].create({
            'partner_id': self.id,
            'amount': -amount,
            'transaction_type': 'debit',
            'description': description,
            'reference': self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/',
        })
