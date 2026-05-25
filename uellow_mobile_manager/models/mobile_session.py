# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class MobileSession(models.Model):
    _name = 'mobile.session'
    _description = 'Mobile App Active Sessions'
    _order = 'last_activity desc'

    # Identity
    device_id = fields.Char(string='Device ID', required=True, index=True)
    device_name = fields.Char(string='Device Name')
    platform = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
    ], string='Platform')
    app_version = fields.Char(string='App Version')
    os_version = fields.Char(string='OS Version')

    # User — stored as Char to avoid any inverse field issues
    odoo_user_id = fields.Integer(string='Odoo User ID', default=0, index=True)
    customer_name = fields.Char(string='Customer Name')
    customer_email = fields.Char(string='Customer Email')
    is_guest = fields.Boolean(string='Guest Session', default=True)

    # Session info
    session_token = fields.Char(string='Session Token', index=True)
    fcm_token = fields.Char(string='FCM Push Token')
    ip_address = fields.Char(string='IP Address')
    country_code = fields.Char(string='Country Code', size=3)

    # Activity
    first_seen = fields.Datetime(string='First Seen', default=fields.Datetime.now)
    last_activity = fields.Datetime(string='Last Activity', default=fields.Datetime.now)
    is_active = fields.Boolean(
        string='Currently Active', default=True,
        compute='_compute_is_active', store=True
    )

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    @api.depends('last_activity')
    def _compute_is_active(self):
        threshold = datetime.now() - timedelta(minutes=30)
        for rec in self:
            rec.is_active = bool(rec.last_activity and rec.last_activity > threshold)

    @api.model
    def get_active_count(self):
        threshold = datetime.now() - timedelta(minutes=30)
        return self.search_count([('last_activity', '>=', threshold)])

    @api.model
    def register_session(self, device_id, platform, app_version, fcm_token=None,
                         user_id=None, device_name=None, os_version=None, ip=None):
        """Called by Flutter app on launch / login."""
        existing = self.search([('device_id', '=', device_id)], limit=1)
        vals = {
            'last_activity': datetime.now(),
            'app_version': app_version,
            'is_guest': not user_id,
        }
        if fcm_token:
            vals['fcm_token'] = fcm_token
        if user_id:
            try:
                user = self.env['res.users'].sudo().browse(int(user_id))
                vals['odoo_user_id'] = user.id
                vals['customer_name'] = user.partner_id.name or ''
                vals['customer_email'] = user.email or ''
            except Exception:
                pass
        if existing:
            existing.write(vals)
            return existing.id
        else:
            vals.update({
                'device_id': device_id,
                'platform': platform or 'android',
                'device_name': device_name or '',
                'os_version': os_version or '',
                'ip_address': ip or '',
                'first_seen': datetime.now(),
            })
            return self.create(vals).id
