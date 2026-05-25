# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MobileProductSlider(models.Model):
    _name = 'mobile.product.slider'
    _description = 'Mobile App Home Product Slider Section'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Section Title', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Title')
    sequence = fields.Integer(string='Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    section_type = fields.Selection([
        ('flash_sale', 'Flash Sale'),
        ('brand', 'Brand Section'),
        ('category', 'Category Products'),
        ('manual', 'Manually Selected'),
        ('new_arrivals', 'New Arrivals'),
        ('best_sellers', 'Best Sellers'),
        ('tag', 'By Product Tag'),
    ], string='Section Type', default='manual', required=True)

    # Style
    display_style = fields.Selection([
        ('horizontal_scroll', 'Horizontal Scroll'),
        ('grid_2col', '2-Column Grid'),
        ('grid_3col', '3-Column Grid'),
        ('large_cards', 'Large Cards'),
    ], string='Display Style', default='horizontal_scroll')

    show_discount_badge = fields.Boolean(string='Show Discount Badge', default=True)
    show_sold_count = fields.Boolean(string='Show Sold Count', default=True)
    show_rating = fields.Boolean(string='Show Rating', default=True)
    show_view_more = fields.Boolean(string='Show "More" Button', default=True)
    show_timer = fields.Boolean(string='Show Countdown Timer', default=False)
    timer_end = fields.Datetime(string='Timer End Date')

    # Source
    category_id = fields.Many2one('product.public.category', string='Category')
    brand_attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Brand',
        domain=[('attribute_id.name', 'ilike', 'brand')]
    )
    product_tag_id = fields.Many2one('product.tag', string='Product Tag')
    product_ids = fields.Many2many(
        'product.template',
        'mobile_product_slider_template_rel',
        'slider_id', 'product_id',
        string='Manual Products',
        help='Used when Section Type is Manually Selected'
    )
    max_products = fields.Integer(string='Max Products to Show', default=10)

    # "More" button action
    more_action_type = fields.Selection([
        ('category', 'Go to Category'),
        ('search', 'Search Keyword'),
        ('url', 'Custom URL'),
    ], string='"More" Button Action', default='category')
    more_category_id = fields.Many2one('product.public.category', string='More → Category')
    more_url = fields.Char(string='More → URL')
    more_search = fields.Char(string='More → Search Keyword')

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    product_count = fields.Integer(string='Products', compute='_compute_product_count')

    @api.depends('product_ids', 'section_type', 'category_id')
    def _compute_product_count(self):
        for rec in self:
            if rec.section_type == 'manual':
                rec.product_count = len(rec.product_ids)
            else:
                rec.product_count = 0
