# -*- coding: utf-8 -*-
"""Category header slides — shown as an image slider at the top of the
app's Shop page for each MAIN category. Managed from the category form
(Website ▸ eCommerce ▸ Categories ▸ App Slides tab)."""
from odoo import fields, models


class MobileCategorySlide(models.Model):
    _name = 'mobile.category.slide'
    _description = 'Mobile shop category header slide'
    _order = 'sequence, id'

    name = fields.Char(string='Label', help='Internal label (not shown in app)')
    category_id = fields.Many2one(
        'product.public.category', required=True, ondelete='cascade',
        string='Category', index=True)
    image = fields.Image(string='Slide Image', required=True, max_width=1600)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one(
        'website', string='Website',
        help='Leave empty to show on all websites')
    link_type = fields.Selection([
        ('none', 'No link'),
        ('product', 'Product'),
        ('category', 'Category'),
        ('url', 'URL'),
    ], default='none', required=True, string='Tap action')
    link_product_id = fields.Many2one('product.template', string='Product')
    link_category_id = fields.Many2one('product.public.category',
                                       string='Target category')
    link_url = fields.Char(string='URL')

    def to_public_dict(self, base=''):
        self.ensure_one()
        link = {'type': 'none', 'value': ''}
        if self.link_type == 'product' and self.link_product_id:
            link = {'type': 'product', 'value': self.link_product_id.id}
        elif self.link_type == 'category' and self.link_category_id:
            link = {'type': 'category', 'value': self.link_category_id.id}
        elif self.link_type == 'url' and self.link_url:
            link = {'type': 'url', 'value': self.link_url}
        return {
            'id': self.id,
            'image_url': '/api/mobile/v2/category-slide/%d/image?u=%s' % (
                self.id, (self.write_date or fields.Datetime.now())
                .strftime('%Y%m%d%H%M%S')),
            'link': link,
        }


class ProductPublicCategorySlides(models.Model):
    _inherit = 'product.public.category'

    uellow_slide_ids = fields.One2many(
        'mobile.category.slide', 'category_id', string='App Header Slides')
