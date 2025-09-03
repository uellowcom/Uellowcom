# -*- coding: utf-8 -*-
import logging
import uuid
import hashlib
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class MobileUser(models.Model):
    _name = 'mobile.user'
    _description = 'Mobile User'
    _rec_name = 'username'
    
    username = fields.Char(string='Username', required=True, index=True)
    password_hash = fields.Char(string='Password Hash', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade')
    active = fields.Boolean(default=True)
    last_login = fields.Datetime(string='Last Login')
    device_id = fields.Char(string='Device ID')
    device_token = fields.Char(string='Device Token')
    device_platform = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
    ], string='Device Platform')
    
    _sql_constraints = [
        ('username_uniq', 'unique(username)', 'Username must be unique!')
    ]
    
    @api.model
    def create(self, vals):
        """Override create to hash the password"""
        if vals.get('password'):
            vals['password_hash'] = self._hash_password(vals.pop('password'))
        return super(MobileUser, self).create(vals)
    
    def write(self, vals):
        """Override write to hash the password"""
        if vals.get('password'):
            vals['password_hash'] = self._hash_password(vals.pop('password'))
        return super(MobileUser, self).write(vals)
    
    def _hash_password(self, password):
        """Hash the password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        return self.password_hash == self._hash_password(password)
    
    @api.model
    def authenticate(self, username, password):
        """Authenticate a user with username and password"""
        user = self.search([('username', '=', username), ('active', '=', True)], limit=1)
        if not user:
            return False
        
        if not user.check_password(password):
            return False
        
        user.write({
            'last_login': fields.Datetime.now()
        })
        return user
    
    @api.model
    def signup(self, values):
        """Sign up a new mobile user"""
        # Check required fields
        required_fields = ['username', 'password', 'name']
        missing_fields = [field for field in required_fields if field not in values]
        if missing_fields:
            raise ValidationError(_('Missing required fields: %s') % ', '.join(missing_fields))
        
        # Check if username already exists
        if self.search_count([('username', '=', values['username'])]):
            raise ValidationError(_('Username already exists'))
        
        # Create partner if not exists
        partner_values = {
            'name': values.get('name'),
            'email': values.get('email'),
            'phone': values.get('phone'),
            'mobile': values.get('mobile'),
        }
        partner = self.env['res.partner'].create(partner_values)
        
        # Create user if not exists
        user_values = {
            'name': values.get('name'),
            'login': values.get('email') or values.get('username'),
            'partner_id': partner.id,
        }
        user = self.env['res.users'].create(user_values)
        
        # Create mobile user
        mobile_user_values = {
            'username': values['username'],
            'password': values['password'],  # Will be hashed in create method
            'partner_id': partner.id,
            'user_id': user.id,
            'device_id': values.get('device_id'),
            'device_token': values.get('device_token'),
            'device_platform': values.get('device_platform'),
        }
        mobile_user = self.create(mobile_user_values)
        
        return mobile_user
