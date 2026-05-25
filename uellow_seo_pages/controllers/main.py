from odoo import http
from odoo.http import request


class SEOPageController(http.Controller):

    @http.route('/l/<string:slug>', type='http', auth='public', website=True)
    def seo_landing(self, slug, **kw):
        page = request.env['uellow.seo.page'].sudo().search([
            ('slug', '=', slug),
            ('active', '=', True),
        ], limit=1)
        if not page:
            return request.not_found()

        # Track visit
        page.sudo().write({
            'visit_count': page.visit_count + 1,
            'last_visited': __import__('odoo').fields.Datetime.now(),
        })

        products = page.get_products(page.max_products)
        lang = request.env.lang or 'en_US'
        is_arabic = 'ar' in lang

        return request.render('uellow_seo_pages.seo_landing_page', {
            'page': page,
            'products': products,
            'is_arabic': is_arabic,
            'title': page.title_ar if is_arabic and page.title_ar else page.title_en,
            'h1': page.h1_ar if is_arabic and page.h1_ar else page.h1_en or page.title_en,
            'intro': page.intro_ar if is_arabic and page.intro_ar else page.intro_en or '',
        })
