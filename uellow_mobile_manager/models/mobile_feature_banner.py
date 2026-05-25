# -*- coding: utf-8 -*-
from odoo import models, fields


class MobileFeatureBanner(models.Model):
    _name = 'mobile.feature.banner'
    _description = 'Mobile App Feature Banner (Trust Badges)'
    _order = 'sequence asc'

    name = fields.Char(string='Feature Title', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Title')
    description = fields.Char(string='Subtitle', translate=True)
    description_ar = fields.Char(string='Arabic Subtitle')
    sequence = fields.Integer(string='Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    icon_type = fields.Selection([
        ('image', 'Custom Image'),
        ('emoji', 'Emoji / Text Icon'),
    ], string='Icon Type', default='emoji')

    icon_image = fields.Binary(string='Icon Image', attachment=True)
    icon_emoji = fields.Char(string='Emoji / Icon Text', default='🛡️')

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )
