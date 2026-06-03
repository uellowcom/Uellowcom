from odoo import http
from odoo.http import request


class WebsiteFlashDeals(http.Controller):
    """Public-facing /flash-deals page that mirrors the mobile app's
    Flash Sale screen. Reads live mobile.flash.sale records so the admin
    only configures things in one place."""

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
