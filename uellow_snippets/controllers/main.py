from odoo import http
from odoo.http import request
import json


class UellowNewArrivals(http.Controller):

    @http.route(
        '/uellow/new-arrivals',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors='*',
    )
    def new_arrivals(self, limit=24, lang='ar_001', **kwargs):
        try:
            # جيب الـ website الحالي تلقائياً
            website = request.env['website'].sudo().get_current_website()
            website_id = website.id if website else 1

            env = request.env(context={
                'lang': lang,
                'website_id': website_id,
            })

            domain = [
                ('is_published', '=', True),
                ('sale_ok',      '=', True),
                '|',
                ('website_id',   '=', False),
                ('website_id',   '=', website_id),
            ]

            products = env['product.template'].sudo().search_read(
                domain=domain,
                fields=[
                    'id', 'name', 'list_price', 'compare_list_price',
                    'website_url', 'description_sale',
                    'rating_avg', 'rating_count',
                ],
                limit=int(limit),
                order='id desc',
            )

            return request.make_response(
                json.dumps({
                    'status': 'ok',
                    'products': products,
                    'website_id': website_id,
                }),
                headers=[
                    ('Content-Type', 'application/json; charset=utf-8'),
                    ('Access-Control-Allow-Origin', '*'),
                    ('Cache-Control', 'public, max-age=60'),
                ],
            )
        except Exception as e:
            return request.make_response(
                json.dumps({'status': 'error', 'message': str(e)}),
                headers=[('Content-Type', 'application/json; charset=utf-8')],
            )
