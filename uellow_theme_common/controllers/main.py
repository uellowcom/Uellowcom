# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol Infotech Private Limited. (<https://www.droggol.com/>)

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.product_configurator import WebsiteSaleProductConfiguratorController


class DroggolThemeCommon(http.Controller):

    @http.route(['/uellow_theme_common/design_content/<model("dr.website.content"):content>'], type='http', website=True, auth='user')
    def design_content(self, content, **post):
        return request.render('uellow_theme_common.design_content', {'content': content, 'no_header': True, 'no_footer': True})


class UellowSearchSuggest(http.Controller):
    """Inline autocomplete endpoint for the header search box.

    Returns a small JSON document with three sections (products,
    categories, brands), each capped at a few entries. The header JS
    paints these into a dropdown directly under the input — same data
    shape as the theme's sidebar, but rendered inline.
    """

    @http.route('/uc/search_suggest', type='json', auth='public',
                website=True, csrf=False)
    def search_suggest(self, q='', **kw):
        q = (q or '').strip()
        if len(q) < 2:
            return {'products': [], 'categories': [], 'brands': []}

        website = request.website
        Product = request.env['product.template'].sudo()
        Cat     = request.env['product.public.category'].sudo()
        Brand   = request.env['product.attribute.value'].sudo()

        # ── Products ──────────────────────────────────────────────────
        product_domain = website.sale_product_domain() if hasattr(website, 'sale_product_domain') else []
        product_domain = list(product_domain) + [
            ('name', 'ilike', q),
            ('is_published', '=', True),
            ('website_id', 'in', [False, website.id]),
        ]
        products = Product.search(product_domain, limit=6)

        # ── Categories ────────────────────────────────────────────────
        cats = Cat.search([
            '|', ('name', 'ilike', q), ('parents_and_self.name', 'ilike', q),
            ('website_id', 'in', [False, website.id]),
        ], limit=4) if hasattr(Cat, 'parents_and_self') else Cat.search([
            ('name', 'ilike', q),
            ('website_id', 'in', [False, website.id]),
        ], limit=4)

        # ── Brands (attribute values on the configured brand attributes) ─
        brands = Brand
        try:
            brand_attr_ids = website._get_brand_attributes().ids if hasattr(website, '_get_brand_attributes') else []
            if brand_attr_ids:
                brands = Brand.search([
                    ('attribute_id', 'in', brand_attr_ids),
                    ('name', 'ilike', q),
                ], limit=4)
        except Exception:
            pass

        # ── Shape the response ────────────────────────────────────────
        def _img_url(model, rid, field='image_128'):
            return '/web/image/%s/%s/%s' % (model, rid, field)

        return {
            'q': q,
            'products': [{
                'name':  p.display_name or p.name,
                'price': p.list_price,
                'url':   '/shop/%s' % (p.website_url and p.website_url.split('/')[-1] or p.id),
                'image': _img_url('product.template', p.id),
            } for p in products],
            'categories': [{
                'name': c.complete_name if hasattr(c, 'complete_name') else c.name,
                'url':  '/shop/category/%s' % c.id,
                'image': _img_url('product.public.category', c.id) if c.image_128 else None,
            } for c in cats],
            'brands': [{
                'name': b.name,
                'url':  '/shop?attribute_value=%s' % b.id,
                'image': _img_url('product.attribute.value', b.id, 'image') if b.image else None,
            } for b in brands],
        }


class DroggolThemeCommonSaleProductConfiguratorController(WebsiteSaleProductConfiguratorController):

    def _get_product_information(self, product_template, combination, currency, pricelist, so_date, quantity=1, product_uom_id=None, parent_combination=None, **kwargs):
        result = super()._get_product_information(product_template, combination, currency, pricelist, so_date, quantity=quantity, product_uom_id=product_uom_id, parent_combination=parent_combination, **kwargs)
        result['extraInfo'] = {
            ptav.id: {
                'dr_thumb_image': ptav.dr_thumb_image,
                'dr_image': ptav.dr_image,
            } for ptav in product_template.attribute_line_ids.product_template_value_ids
        }
        return result
