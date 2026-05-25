# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MobileSlider(models.Model):
    _name = 'mobile.slider'
    _description = 'Mobile App Hero Slider'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Slide Title', required=True)
    sequence = fields.Integer(string='Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    # Images
    image = fields.Binary(string='Slide Image', required=True, attachment=True)
    image_filename = fields.Char(string='Image Filename')

    # Link / Action
    action_type = fields.Selection([
        ('none', 'No Action'),
        ('product', 'Open Product'),
        ('category', 'Open Category'),
        ('url', 'External URL'),
        ('search', 'Search Keyword'),
    ], string='On Tap Action', default='none', required=True)

    product_id = fields.Many2one('product.template', string='Product')
    category_id = fields.Many2one('product.public.category', string='Category')
    url = fields.Char(string='URL / Deep Link')
    search_keyword = fields.Char(string='Search Keyword')

    # Display settings
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise models.ValidationError('End date must be after start date.')

    def get_slider_data(self):
        """Return slider data for API."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        result = []
        for slider in self:
            action_value = None
            if slider.action_type == 'product' and slider.product_id:
                action_value = slider.product_id.id
            elif slider.action_type == 'category' and slider.category_id:
                action_value = slider.category_id.id
            elif slider.action_type == 'url':
                action_value = slider.url
            elif slider.action_type == 'search':
                action_value = slider.search_keyword

            result.append({
                'id': slider.id,
                'name': slider.name,
                'image_url': f"{base_url}/web/image/mobile.slider/{slider.id}/image",
                'action_type': slider.action_type,
                'action_value': action_value,
                'sequence': slider.sequence,
            })
        return result
