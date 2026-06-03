from odoo import http
from odoo.http import request


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
