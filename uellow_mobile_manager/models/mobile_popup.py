# -*- coding: utf-8 -*-
from odoo import models, fields


class MobilePopup(models.Model):
    _name = 'mobile.popup'
    _description = 'Mobile App Popup / Interstitial Banner'
    _order = 'sequence asc'

    name = fields.Char(string='Popup Name', required=True)
    sequence = fields.Integer(string='Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    image = fields.Binary(string='Popup Image', required=True, attachment=True)
    image_filename = fields.Char(string='Image Filename')

    trigger = fields.Selection([
        ('app_open', 'On App Open'),
        ('home', 'On Home Page Load'),
        ('first_open', 'First App Open Only'),
        ('after_login', 'After Login'),
    ], string='Show Trigger', default='app_open')

    frequency = fields.Selection([
        ('always', 'Every Time'),
        ('once_per_day', 'Once Per Day'),
        ('once_per_session', 'Once Per Session'),
        ('once_ever', 'Once Ever'),
    ], string='Show Frequency', default='once_per_session')

    action_type = fields.Selection([
        ('none', 'Dismiss Only'),
        ('product', 'Open Product'),
        ('category', 'Open Category'),
        ('url', 'Open URL'),
    ], string='On Tap Action', default='none')

    product_id = fields.Many2one('product.template', string='Product')
    category_id = fields.Many2one('product.public.category', string='Category')
    action_url = fields.Char(string='URL')

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )
