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
    def get_products(self, limit=10, offset=0, product_id=None,
                     category_id=None, **kwargs):
        """Public endpoint — recommended products for the current website.

        When a ``product_id`` (or ``category_id``) is supplied it recommends
        RELATED products (same public category as the viewed product), filling
        with the merchandised catalogue; otherwise it returns the merchandised
        catalogue. Backward-compatible: same response shape/fields as before.

        Ordered by ``website_sequence`` (a STORED field) — never by
        rating_avg / sales_count, which are non-stored computes and raise
        "Cannot convert to SQL" when used as a search order.
        """
        website = request.website
        website_id = website.id if website else 1
        Tmpl = request.env['product.template'].sudo()
        limit = int(limit or 10)
        offset = int(offset or 0)
        need = limit + offset

        base = [
            ('is_published', '=', True),
            ('website_id', 'in', [False, website_id]),
        ]
        fields = [
            'name', 'list_price', 'compare_list_price', 'website_url', 'id',
            'rating_avg', 'rating_count', 'qty_available',
            'allow_out_of_stock_order',
        ]

        # Relevance signal: the public categories of the viewed product.
        categ_ids = []
        pid = int(product_id) if product_id else 0
        if pid:
            cur = Tmpl.browse(pid)
            if cur.exists():
                categ_ids = cur.public_categ_ids.ids
        elif category_id:
            categ_ids = [int(category_id)]

        ids = []
        if categ_ids:
            dom = base + [('public_categ_ids', 'in', categ_ids)]
            if pid:
                dom += [('id', '!=', pid)]
            ids = Tmpl.search(dom, limit=need,
                              order='website_sequence, id desc').ids
        # Fill with the merchandised catalogue if not enough related products.
        if len(ids) < need:
            dom = list(base)
            if pid:
                dom += [('id', '!=', pid)]
            if ids:
                dom += [('id', 'not in', ids)]
            ids += Tmpl.search(dom, limit=need,
                               order='website_sequence, id desc').ids

        recs = Tmpl.browse(ids[offset:offset + limit])
        products = recs.read(fields)
        return {'products': products, 'count': len(products)}
