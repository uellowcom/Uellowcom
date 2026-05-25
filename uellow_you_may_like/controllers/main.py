# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class UellowYouMayLike(http.Controller):

    @http.route(
        '/uellow/products',
        type='json',
        auth='public',          # ← يعمل للزوار بدون تسجيل دخول
        methods=['POST'],
        website=True,
        csrf=False,
    )
    def get_products(self, limit=10, offset=0, **kwargs):
        """
        Public endpoint – returns published products for the current website.
        Accessible by guests (auth='public').
        """
        website = request.website
        website_id = website.id if website else 1

        domain = [
            ('is_published', '=', True),
            ('website_id', 'in', [False, website_id]),
        ]

        products = request.env['product.template'].sudo().search_read(
            domain=domain,
            fields=[
                'name',
                'list_price',
                'compare_list_price',
                'website_url',
                'id',
                'rating_avg',
                'rating_count',
                'qty_available',
                'allow_out_of_stock_order',
            ],
            limit=int(limit),
            offset=int(offset),
            order='id desc',
        )

        return {'products': products, 'count': len(products)}
