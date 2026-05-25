# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
from odoo import models, fields, api, _
from odoo.http import request

class FacebookProductDataFeed(models.Model):
    _name = 'facebook.product.data.feed'
    _description = "Facebook Product Data Feed"

    @api.model
    def _default_feed_model_domain(self):
        return [('is_published', '=', True)]

    name = fields.Char('Name')
    feed_url = fields.Char(
        string='Feed Download URL',
        readonly=True,
    )
    shop_model_domain = fields.Char(
        string='Feed Model domain',
        help='The model domain for the feed.',
        default=_default_feed_model_domain,
    )
    shop_model_name = fields.Char(
        related='shop_model_id.model',
        string='Model Name',
    )
    shop_model_id = fields.Many2one(
        comodel_name='ir.model',
        string='Model',
        domain=[('model', 'in', ['product.product', 'product.template'])],
        ondelete='cascade',
        required=True,
    )
    shop_fields_ids = fields.One2many(
        'shop.fields',
        'facebook_feed_id',
        string='Shop Fields'
    )
    sale_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string='Sale Pricelist',
        help="Price list with discounted prices.",
        ondelete='set null',
    )
    file_format = fields.Selection([('csv', 'CSV'), ('tsv', 'TSV'), ('xml', 'XML')], default='csv')

    def action_create_feed_token(self):
        IrConfigParam = self.env["ir.config_parameter"].sudo()
        base_url = IrConfigParam.get_param("web.base.url", False)
        for feed in self:
            if base_url:
                if feed.file_format == 'csv':
                    feed.feed_url = f"{base_url}/{feed.id}/product/csv"
                elif feed.file_format == 'tsv':
                    feed.feed_url = f"{base_url}/{feed.id}/product/tsv"
                elif feed.file_format == 'xml':
                    feed.feed_url = f"{base_url}/{feed.id}/product/xml"
                else:
                    feed.feed_url = "Error: Invalid file format"
            else:
                feed.feed_url = "Error: web.base.url not set"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'shop_fields_ids' in fields_list:
            existing_fields = self.env['shop.fields'].search([])
            res['shop_fields_ids'] = [(4, f.id) for f in existing_fields]
        return res

    @api.onchange('shop_model_id')
    def onchange_shop_model(self):
        if not self.shop_model_id:
            return
        model_name = self.shop_model_id.model
        all_model_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', model_name)
        ])
        mapping = {
            'title': 'name',
            'price': 'list_price',
            'condition': 'condition',
            'availability': 'sale_ok',
            'link': 'website_url',
            'image_link': 'image_1920',
            'brand': 'brand_id',
            'quantity_to_sell_on_facebook': 'qty_available',
            'size': 'size',
            'sale_price': 'list_price',
            'item_group_id': 'categ_id',
            'status': 'active',
            'gtin': 'gtin',
            'mpn': 'mpn',
            'shipping_weight': 'weight',
            'availability_date': 'availability_date',
            'product_type': 'type',
            'product_detail': 'description_sale',
            'cost_of_goods_sold': 'standard_price',
            'fb_product_category': 'facebook_category_id',
            'google_product_category': 'google_category_id',
            'sale_price_effective_date': None,
            'rich_text_description': 'description'
        }
        for line in self.shop_fields_ids:
            field_name = mapping.get(line.name, line.name)
            matched = all_model_fields.filtered(lambda f: f.name == field_name)
            if matched:
                line.field_id = matched.id
