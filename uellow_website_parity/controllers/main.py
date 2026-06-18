import base64
from odoo import http
from odoo.http import request


class UellowReport(http.Controller):
    """Serves internal HTML reports as a real rendered page (text/html, no
    nosniff) so they always render colourfully in the browser instead of
    showing raw text like a downloaded attachment."""

    @http.route('/site-report', type='http', auth='public', website=False,
                sitemap=False, csrf=False)
    def site_report(self, name='uellow-website-full-report.html', **kw):
        att = request.env['ir.attachment'].sudo().search(
            [('name', '=', name)], order='id desc', limit=1)
        if not att or not att.datas:
            return request.not_found()
        html = base64.b64decode(att.datas)
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')])


class WebsiteFlashDeals(http.Controller):
    """Public-facing /flash-deals page that mirrors the mobile app's
    Flash Sale screen. Reads live mobile.flash.sale records so the admin
    only configures things in one place."""

    @http.route('/free-shipping', type='http', auth='public', website=True,
                sitemap=True)
    def free_shipping_page(self, **kw):
        """Products eligible for free shipping (product flag, category,
        or tag). Reuses the same _is_free_shipping helper the mobile API
        uses so both surfaces stay in sync."""
        Tmpl = request.env['product.template'].sudo()
        base = [('is_published', '=', True), ('active', '=', True)]
        candidates = Tmpl.search(base, order='create_date desc', limit=300)
        products = candidates.filtered(
            lambda p: hasattr(p, '_is_free_shipping') and p._is_free_shipping())
        return request.render('uellow_website_parity.free_shipping_page', {
            'products': products[:60],
            'total': len(products),
        })

    @http.route('/brands', type='http', auth='public', website=True,
                sitemap=True)
    def brands_page(self, **kw):
        """All brands as a grid (like Shop-by-Category). Each brand is a
        product.attribute.value with a dr_image icon (set per-brand in the
        admin). Links to the shop filtered by that brand."""
        website = request.env['website'].sudo().get_current_website()
        brands = website._get_brands(order='name')
        return request.render('uellow_website_parity.brands_page', {
            'brands': brands,
            'total': len(brands),
        })

    @http.route('/bestseller', type='http', auth='public', website=True,
                sitemap=True)
    def bestseller_page(self, **kw):
        """Best-selling products — reuses the SAME ranking engine the mobile
        app uses (uellow.product.rank), so the website and app agree. Falls
        back to sale-quantity ordering, then to newest, on empty data."""
        Tmpl = request.env['product.template'].sudo()
        website = request.env['website'].sudo().get_current_website()
        products = Tmpl.browse()
        Rank = request.env.get('uellow.product.rank')
        if Rank is not None:
            try:
                ranks = Rank.sudo().search(
                    ['|', ('website_id', '=', False),
                     ('website_id', '=', website.id)],
                    order='score desc', limit=200)
                seen, ids = set(), []
                for r in ranks:
                    t = r.product_tmpl_id
                    if t and t.id not in seen and t.is_published and t.active:
                        seen.add(t.id)
                        ids.append(t.id)
                products = Tmpl.browse(ids[:60])
            except Exception:
                products = Tmpl.browse()
        if not products:
            products = Tmpl.search(
                [('is_published', '=', True), ('active', '=', True)],
                order='sales_count desc', limit=60)
        return request.render('uellow_website_parity.bestseller_page', {
            'products': products[:60],
            'total': len(products),
        })

    @http.route('/flash-deals', type='http', auth='public', website=True,
                sitemap=True)
    def flash_deals_page(self, **kw):
        Sale = request.env['mobile.flash.sale'].sudo()
        website = request.env['website'].sudo().get_current_website()
        sales = Sale.search([
            ('active', '=', True),
            '|', ('website_id', '=', False), ('website_id', '=', website.id),
        ], order='sequence asc')
        # Hand them all to the template; the template decides how to split
        # them into live / upcoming / ended sections.
        return request.render('uellow_website_parity.flash_deals_page', {
            'sales': sales,
            'page_title': 'Flash deals · صفقات سريعة',
        })
