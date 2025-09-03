# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MobileDevice(models.Model):
    _name = 'mobile.device'
    _description = 'Mobile Device'
    _rec_name = 'device_id'

    partner_id = fields.Many2one('res.partner', string='User', required=True)
    device_id = fields.Char(string='Device ID', required=True)
    device_type = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('other', 'Other')
    ], string='Device Type', required=True)
    device_model = fields.Char(string='Device Model')
    app_version = fields.Char(string='App Version')
    os_version = fields.Char(string='OS Version')
    push_token = fields.Text(string='Push Token')
    last_used = fields.Datetime(string='Last Used')
    is_active = fields.Boolean(string='Is Active', default=True)

    _sql_constraints = [
        ('unique_device_partner', 'unique(device_id, partner_id)', 'Device ID must be unique per user!')
    ]
