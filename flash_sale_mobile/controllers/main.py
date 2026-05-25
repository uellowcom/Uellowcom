# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class FlashSaleMobile(http.Controller):

    @http.route(
        '/flash_sale_mobile/products',
        type='json',
        auth='public',
        website=True,
        sitemap=False,
    )
    def get_flash_products(self, category_id=871, limit=12, **kwargs):
        try:
            cat_id  = int(category_id)
            website = request.env['website'].get_current_website()
            PT      = request.env['product.template'].sudo()

            domain = [
                ['public_categ_ids', 'in', [cat_id]],
                ['is_published', '=', True],
                ['website_id', 'in', [False, website.id]],
            ]

            # ✅ search_read مباشر — بدون أي دوال غير موجودة
            products = PT.search_read(
                domain,
                fields=['id', 'name', 'list_price', 'compare_list_price', 'website_url'],
                limit=int(limit),
                order='website_sequence asc',
            )

            return {'success': True, 'products': products}

        except Exception as e:
            import logging
            logging.getLogger(__name__).warning('FlashSaleMobile error: %s', e)
            return {'success': False, 'error': str(e), 'products': []}
