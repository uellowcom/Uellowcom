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
        
        # Create transaction record
        self.env['mobile.wallet.transaction'].create({
            'partner_id': self.id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': description,
        })
    
    def deduct_wallet_balance(self, amount, description=""):
        """Deduct amount from wallet balance"""
        self.ensure_one()
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))
        
        if self.wallet_balance < amount:
            raise ValidationError(_('Insufficient wallet balance'))
        
        self.wallet_balance -= amount
        
        # Create transaction record
        self.env['mobile.wallet.transaction'].create({
            'partner_id': self.id,
            'amount': -amount,
            'transaction_type': 'debit',
            'description': description,
        })


class MobileDevice(models.Model):
    _name = 'mobile.device'
    _description = 'Mobile Device'
    _order = 'last_used desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    device_id = fields.Char('Device ID', required=True)
    device_type = fields.Selection([
        ('ios', 'iOS'),
        ('android', 'Android'),
    ], string='Device Type', required=True)
    device_model = fields.Char('Device Model')
    app_version = fields.Char('App Version')
    os_version = fields.Char('OS Version')
    push_token = fields.Char('Push Token')
    last_used = fields.Datetime('Last Used', default=fields.Datetime.now)
    is_active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('unique_device_partner', 'unique(device_id, partner_id)', 'Device already registered for this user.'),
    ]

    @api.model
    def register_device(self, partner_id, device_data):
        """Register or update mobile device"""
        device = self.search([
            ('device_id', '=', device_data.get('device_id')),
            ('partner_id', '=', partner_id)
        ], limit=1)
        
        if device:
            device.write({
                'device_type': device_data.get('device_type'),
                'device_model': device_data.get('device_model'),
                'app_version': device_data.get('app_version'),
                'os_version': device_data.get('os_version'),
                'push_token': device_data.get('push_token'),
                'last_used': fields.Datetime.now(),
                'is_active': True,
            })
        else:
            device_data.update({
                'partner_id': partner_id,
                'last_used': fields.Datetime.now(),
                'is_active': True,
            })
            device = self.create(device_data)
        
        return device
