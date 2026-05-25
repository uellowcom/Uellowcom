# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request

class FlashSaleController(http.Controller):

    @http.route('/flash_sale/products', type='http', auth='public', website=True, csrf=False)
    def get_flash_products(self, categ_id=871, limit=18, lang='en_US', **kwargs):
        env = request.env(context={'lang': lang})
        products = env['product.template'].sudo().search_read(
            domain=[
                ('public_categ_ids', 'in', [int(categ_id)]),
                ('is_published', '=', True),
            ],
            fields=['name', 'list_price', 'compare_list_price', 'website_url', 'id'],
            limit=int(limit),
            order='id desc',
        )
        return request.make_response(
            json.dumps({'result': products}),
            headers=[('Content-Type', 'application/json')]
        )
