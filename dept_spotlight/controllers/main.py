# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class DeptSpotlightController(http.Controller):

    @http.route(
        '/dsp/products',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        website=True,
        sitemap=False,
    )
    def dsp_products(self, categ_id='', **kw):
        try:
            env     = request.env
            website = env['website'].sudo().get_current_website()

            # language
            lang_code = request.context.get('lang') or website.default_lang_id.code or 'en_US'
            is_arabic = lang_code.startswith('ar')

            # currency — single lookup, no loop
            try:
                pricelist  = website.get_current_pricelist()
                cur_symbol = pricelist.currency_id.name
            except Exception:
                pricelist  = None
                cur_symbol = website.company_id.currency_id.name or 'KWD'

            # parse requested category IDs
            raw_ids = [x.strip() for x in (categ_id or '').split(',') if x.strip()]
            cat_ids = [int(x) for x in raw_ids if x.isdigit()]

            # base domain — website filter + published only
            base_domain = [
                ('is_published', '=', True),
                ('website_id',   'in', [False, website.id]),
            ]

            ProductTmpl = env['product.template'].sudo().with_context(
                website_id=website.id,
                lang=lang_code,
            )

            # auto-discover: get all public categories, pick those with ≥ 12 products
            # do it in ONE query per category (no price conversion here)
            if not cat_ids:
                all_cats = env['product.public.category'].sudo().search(
                    [], order='sequence asc, id asc', limit=50
                )
                for c in all_cats:
                    cnt = ProductTmpl.search_count(
                        base_domain + [('public_categ_ids', 'child_of', c.id)]
                    )
                    if cnt >= 12:
                        cat_ids.append(c.id)
                    if len(cat_ids) >= 20:
                        break

            results = []
            for cid in cat_ids:
                pub = env['product.public.category'].sudo().browse(cid)
                if not pub.exists():
                    continue

                # fetch exactly 12 products — no extra queries
                products = ProductTmpl.search_read(
                    domain=base_domain + [('public_categ_ids', 'child_of', cid)],
                    fields=['id', 'name', 'list_price'],
                    limit=12,
                    order='id desc',
                )

                if len(products) < 12:
                    continue  # skip categories with fewer than 12 products

                # category names
                try:
                    name_ar = pub.with_context(lang='ar_001').name or pub.name or ''
                except Exception:
                    name_ar = pub.name or ''
                name_en = pub.with_context(lang='en_US').name or pub.name or ''

                rows = []
                for p in products:
                    rows.append({
                        'id':    p['id'],
                        'name':  p['name'],
                        'price': p['list_price'],
                        'cur':   cur_symbol,
                    })

                results.append({
                    'categ_id':      cid,
                    'categ_name_ar': name_ar,
                    'categ_name_en': name_en,
                    'is_arabic':     is_arabic,
                    'rows':          rows,
                })

            body = json.dumps({'ok': True, 'results': results})

        except Exception as e:
            body = json.dumps({'ok': False, 'err': str(e)})

        return request.make_response(body, headers=[
            ('Content-Type',  'application/json; charset=utf-8'),
            ('Cache-Control', 'public, max-age=120'),
        ])

    @http.route(
        '/dsp/category-helper',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
        website=True,
        sitemap=False,
    )
    def dsp_category_helper(self, **kw):
        try:
            env     = request.env
            website = env['website'].sudo().get_current_website()
            tmpl    = env['product.template'].sudo().with_context(website_id=website.id)
            cats    = env['product.public.category'].sudo().search([], order='name asc')
            rows    = ''
            for c in cats:
                try:
                    cnt = tmpl.search_count([
                        ('public_categ_ids', 'child_of', c.id),
                        ('is_published', '=', True),
                        ('website_id', 'in', [False, website.id]),
                    ])
                except Exception:
                    cnt = 0
                color  = '#16a34a' if cnt >= 12 else ('#f59e0b' if cnt > 0 else '#dc2626')
                parent = c.parent_id.name if c.parent_id else '—'
                rows += (
                    '<tr><td style="padding:8px 14px;font-weight:700;color:#7C3AED">' + str(c.id) + '</td>'
                    '<td style="padding:8px 14px">' + _esc(c.name or '') + '</td>'
                    '<td style="padding:8px 14px;color:#888;font-size:12px">' + _esc(parent) + '</td>'
                    '<td style="padding:8px 14px;font-weight:700;color:' + color + '">' + str(cnt) + '</td></tr>'
                )
            html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><title>DSP</title>'
                '<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px}'
                'table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #eee}'
                'th{background:#f9fafb;padding:8px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase}'
                'tr:hover td{background:#fafafa}code{background:#f3f4f6;padding:2px 6px;border-radius:4px}</style>'
                '</head><body><h1 style="font-size:20px;margin-bottom:16px">Category Helper</h1>'
                '<p style="margin-bottom:16px;font-size:13px;color:#555">🟢 ≥12 products = will show. '
                'Paste IDs in editor: <code>603,855,412</code></p>'
                '<table><thead><tr><th>ID</th><th>Name</th><th>Parent</th><th>Products</th></tr></thead>'
                '<tbody>' + rows + '</tbody></table></body></html>')
        except Exception as e:
            html = '<h1>Error: ' + str(e) + '</h1>'
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])


def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
