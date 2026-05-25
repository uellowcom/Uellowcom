# -*- coding: utf-8 -*-
from odoo import models, fields


class MobileCategoryIcon(models.Model):
    _name = 'mobile.category.icon'
    _description = 'Mobile App Home Category Icons'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Label', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Label')
    sequence = fields.Integer(string='Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    icon_image = fields.Binary(string='Icon Image', required=True, attachment=True)
    icon_filename = fields.Char(string='Icon Filename')

    # Action
    action_type = fields.Selection([
        ('category', 'Product Category'),
        ('url', 'Custom URL'),
        ('search', 'Search Keyword'),
    ], string='On Tap Action', default='category', required=True)

    category_id = fields.Many2one('product.public.category', string='Product Category')
    url = fields.Char(string='Custom URL')
    search_keyword = fields.Char(string='Search Keyword')

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    def get_icon_data(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        result = []
        for icon in self:
            action_value = None
            if icon.action_type == 'category' and icon.category_id:
                action_value = icon.category_id.id
            elif icon.action_type == 'url':
                action_value = icon.url
            elif icon.action_type == 'search':
                action_value = icon.search_keyword

            result.append({
                'id': icon.id,
                'name': icon.name,
                'name_ar': icon.name_ar or icon.name,
                'icon_url': f"{base_url}/web/image/mobile.category.icon/{icon.id}/icon_image",
                'action_type': icon.action_type,
                'action_value': action_value,
                'sequence': icon.sequence,
            })
        return result
