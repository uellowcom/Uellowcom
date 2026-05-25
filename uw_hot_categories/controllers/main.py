# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class UwHotCategoriesController(http.Controller):

    @http.route('/uw_hot_cats/data', type='json', auth='public', website=True, csrf=False)
    def get_hot_cats_data(self, cat_ids=None, limit=50, lang=None, **kwargs):
        """
        Public endpoint — returns category names + product IDs
        for the given list of category IDs.
        No authentication required.
        """
        if not cat_ids or not isinstance(cat_ids, list):
            return {'error': 'No cat_ids provided'}

        # Sanitize: only integers allowed
        try:
            cat_ids = [int(c) for c in cat_ids if str(c).isdigit()]
        except Exception:
            return {'error': 'Invalid cat_ids'}

        if not cat_ids:
            return {'error': 'No valid cat_ids'}

        # Determine language context
        env = request.env
        ctx = {}
        if lang:
            ctx['lang'] = lang

        result = {}

        for cat_id in cat_ids:
            # Fetch category name
            cat = env['product.public.category'].with_context(**ctx).sudo().browse(cat_id)
            if not cat.exists():
                continue

            cat_name = cat.name

            # Fetch published products in this category
            products = env['product.template'].with_context(**ctx).sudo().search(
                [
                    ('public_categ_ids', 'child_of', cat_id),
                    ('is_published', '=', True),
                    ('sale_ok', '=', True),
                ],
                limit=limit,
                order='id asc',
            )

            result[str(cat_id)] = {
                'name': cat_name,
                'products': [{'id': p.id, 'name': p.name} for p in products],
            }

        return result
