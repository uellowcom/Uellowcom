"""Flash sale — /api/mobile/v2/flash-sale/*"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, fail, get_lang, bilingual, img_url  # noqa: F401
from .products import serialize_product_card


def _serialize_sale(sale, lang, with_products=True):
    cur = sale.website_id.currency_id
    products = []
    resolved = sale._resolved_products()
    if with_products:
        products = [serialize_product_card(p, lang) for p in resolved]
    # Derive the unique set of public categories across the products so
    # the app can render circular category filter chips on top of the
    # flash sale screen.
    categories = {}
    for p in resolved:
        for c in p.public_categ_ids:
            if c.id not in categories:
                categories[c.id] = {
                    'id': c.id,
                    'name': bilingual(c, 'name'),
                    'image': img_url('product.public.category', c.id,
                                     'image_512', unique=c.write_date)
                            if c.image_512 else None,
                    'count': 1,
                }
            else:
                categories[c.id]['count'] += 1
    cat_list = sorted(categories.values(), key=lambda x: -x['count'])
    return {
        'id': sale.id,
        'title': {'en': sale.name or '', 'ar': sale.name_ar or sale.name or ''},
        'subtitle': {'en': sale.subtitle or '', 'ar': sale.subtitle_ar or sale.subtitle or ''},
        'start_date': sale.start_date and sale.start_date.isoformat() or None,
        'end_date':   sale.end_date and sale.end_date.isoformat() or None,
        'is_live':    sale.is_live,
        'source':     sale.source,
        'display_style': sale.display_style,
        'background_color': sale.background_color or '#F5C320',
        'accent_color':     sale.accent_color or '#FF4D4D',
        'show_countdown':   sale.show_countdown,
        'show_progress':    sale.show_progress,
        'show_view_more':   sale.show_view_more,
        'max_qty_per_user': sale.max_qty_per_user or 0,
        'sold_count':       sale.sold_count,
        'product_count':    len(products),
        'products':         products,
        'categories':       cat_list,
        # Build a map: product_id → first public_categ_id, so the app
        # can filter the product list by tapping a category circle.
        'product_categories': {p.id: (p.public_categ_ids[:1].id or 0)
                                for p in resolved if p.public_categ_ids},
    }


class MobileFlashSaleAPI(http.Controller):

    @http.route('/api/mobile/v2/flash-sales', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_flash_sales(self, **kw):
        """All live flash sales for the current website."""
        lang = get_lang()
        website = request.env['website'].sudo().search([], limit=1)
        Sale = request.env['mobile.flash.sale'].sudo()
        sales = Sale.search([
            ('active', '=', True),
            '|', ('website_id', '=', False), ('website_id', '=', website.id),
        ], order='sequence asc')
        live = sales.filtered(lambda s: s.is_live)
        return ok([_serialize_sale(s, lang) for s in live])

    @http.route('/api/mobile/v2/flash-sales/<int:sale_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def flash_sale_detail(self, sale_id, **kw):
        sale = request.env['mobile.flash.sale'].sudo().browse(sale_id)
        if not sale.exists():
            return fail('NOT_FOUND', 'Flash sale not found', 404)
        return ok(_serialize_sale(sale, get_lang(), with_products=True))
