# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class NewUserBonusController(http.Controller):

    @http.route(
        '/nub/products',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        website=True,
        sitemap=False,
    )
    def nub_products(self, tag_id='17', limit='20', **kw):
        try:
            tag_id = int(tag_id)
            limit  = min(int(limit), 50)

            env      = request.env
            website  = env['website'].sudo().get_current_website()
            lang     = website.default_lang_id.code or 'en_US'

            products = env['product.template'].sudo().with_context(
                website_id=website.id,
                lang=lang,
            ).search_read(
                domain=[
                    ('product_tag_ids', 'in', [tag_id]),
                    ('is_published', '=', True),
                ],
                fields=['id', 'name', 'list_price', 'currency_id'],
                limit=limit,
                order='list_price asc',
            )

            rows = []
            for p in products:
                cid = p.get('currency_id')
                rows.append({
                    'id':    p['id'],
                    'name':  p['name'],
                    'price': p['list_price'],
                    'cur':   cid[1] if isinstance(cid, (list, tuple)) and len(cid) > 1 else 'KWD',
                })

            body = json.dumps({'ok': True, 'rows': rows})
        except Exception as e:
            body = json.dumps({'ok': False, 'err': str(e)})

        return request.make_response(body, headers=[
            ('Content-Type',  'application/json; charset=utf-8'),
            ('Cache-Control', 'public, max-age=60'),
        ])
