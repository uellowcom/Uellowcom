"""
Category endpoints — /api/mobile/v2/categories/*

list           GET   ?parent_id=&depth=2     → flat or tree
tree           GET                           → full hierarchy
detail         GET   /<id>                   → one category + children
products       GET   /<id>/products?...      → products of a category
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, img_url, get_lang, bilingual,
)
from .products import serialize_product_card, _domain_published_for_app


def serialize_category(cat, with_children=False):
    children = []
    if with_children:
        children = [serialize_category(c, with_children=False)
                    for c in cat.child_id.sorted('sequence')]
    return {
        'id': cat.id,
        'name': bilingual(cat, 'name'),
        'parent_id': cat.parent_id.id if cat.parent_id else None,
        'image': img_url('product.public.category', cat.id, 'image_512',
                         unique=cat.write_date) if cat.image_1024 else None,
        'product_count': request.env['product.template'].sudo().search_count(
            _domain_published_for_app() + [('public_categ_ids', 'child_of', cat.id)]
        ),
        'children': children,
    }


class MobileCategoriesAPI(http.Controller):

    @http.route('/api/mobile/v2/categories', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_categories(self, **kw):
        p = get_payload()
        Cat = request.env['product.public.category'].sudo()
        domain = []
        if p.get('parent_id'):
            try:
                domain.append(('parent_id', '=', int(p['parent_id'])))
            except Exception:
                pass
        else:
            domain.append(('parent_id', '=', False))
        cats = Cat.search(domain, order='sequence asc, name asc')
        with_children = str(p.get('with_children', 'false')).lower() in ('1', 'true', 'yes')
        return ok([serialize_category(c, with_children=with_children) for c in cats])

    @http.route('/api/mobile/v2/categories/tree', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def category_tree(self, **kw):
        roots = request.env['product.public.category'].sudo().search(
            [('parent_id', '=', False)], order='sequence asc, name asc',
        )
        return ok([serialize_category(c, with_children=True) for c in roots])

    @http.route('/api/mobile/v2/categories/<int:category_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def category_detail(self, category_id, **kw):
        cat = request.env['product.public.category'].sudo().browse(category_id)
        if not cat.exists():
            return fail('NOT_FOUND', 'Category not found', 404)
        return ok({'category': serialize_category(cat, with_children=True)})

    @http.route('/api/mobile/v2/categories/<int:category_id>/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def category_products(self, category_id, **kw):
        from ._common import paginate
        lang = get_lang()
        p = get_payload()
        cat = request.env['product.public.category'].sudo().browse(category_id)
        if not cat.exists():
            return fail('NOT_FOUND', 'Category not found', 404)
        domain = _domain_published_for_app() + [
            ('public_categ_ids', 'child_of', cat.id),
        ]
        order = {
            'newest': 'create_date desc',
            'price_asc': 'list_price asc',
            'price_desc': 'list_price desc',
            'name': 'name asc',
        }.get(p.get('sort', 'newest'), 'create_date desc')
        recs = request.env['product.template'].sudo().search(domain, order=order)
        items, meta = paginate(
            recs, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )
        return ok(items, meta)

    @http.route('/api/mobile/v2/categories/<int:category_id>/filters', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def category_filters(self, category_id, **kw):
        """Build a filter spec for the category — price range + every
        non-empty attribute (color, size, brand, etc) seen in this
        category's products. Admin can disable specific attributes via
        the `uellow_mobile.hidden_filter_attrs` setting (comma list of
        attribute IDs)."""
        from ._common import bilingual, img_url
        cat = request.env['product.public.category'].sudo().browse(category_id)
        if not cat.exists():
            return fail('NOT_FOUND', 'Category not found', 404)
        domain = _domain_published_for_app() + [
            ('public_categ_ids', 'child_of', cat.id),
        ]
        Tmpl = request.env['product.template'].sudo()
        # Compute price extremes from the same recordset we use below
        recs = Tmpl.search(domain, limit=2000)
        prices = [r.list_price for r in recs if r.list_price]
        min_p = min(prices) if prices else 0.0
        max_p = max(prices) if prices else 0.0

        # Hidden attribute IDs (comma list in settings)
        ICP = request.env['ir.config_parameter'].sudo()
        hidden_csv = ICP.get_param('uellow_mobile.hidden_filter_attrs', '')
        hidden_ids = set()
        for token in (hidden_csv or '').split(','):
            token = token.strip()
            if token.isdigit():
                hidden_ids.add(int(token))

        # Build attribute facets — pull every attribute value used by
        # products in this category, grouped by attribute.
        Line = request.env['product.template.attribute.line'].sudo()
        lines = Line.search([('product_tmpl_id', 'in', recs.ids)])
        attr_buckets = {}
        for line in lines:
            attr = line.attribute_id
            if attr.id in hidden_ids:
                continue
            buck = attr_buckets.setdefault(attr.id, {
                'id': attr.id,
                'name': bilingual(attr, 'name'),
                'display_type': attr.display_type or 'radio',
                'values': {},
            })
            for v in line.value_ids:
                vb = buck['values'].setdefault(v.id, {
                    'id': v.id,
                    'name': bilingual(v, 'name'),
                    'html_color': v.html_color or '',
                    'image': img_url('product.attribute.value', v.id, 'image',
                                     unique=v.write_date) if v.image else None,
                    'count': 0,
                })
                vb['count'] += 1

        filters = []
        for buck in attr_buckets.values():
            buck['values'] = sorted(buck['values'].values(),
                                    key=lambda x: -x['count'])
            filters.append(buck)
        # Sort attributes by total tag count desc (most "useful" first)
        filters.sort(key=lambda b: -sum(v['count'] for v in b['values']))

        return ok({
            'price': {
                'min': round(min_p, 3),
                'max': round(max_p, 3),
                'currency': (cat.env.company.currency_id.symbol or 'KD'),
            },
            'attributes': filters,
        })
