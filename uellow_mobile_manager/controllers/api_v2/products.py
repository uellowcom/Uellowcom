"""
Product endpoints — /api/mobile/v2/products/*
==============================================

list                GET   page, per_page, category, search, sort, brand, ...
detail              GET   /<id>                          → full product
variants            GET   /<id>/variants                 → variant list + options
reviews             GET   /<id>/reviews?page=...         → reviews summary
related             GET   /<id>/related                  → related products
recommended         GET   /recommended                   → personalised
top_selling         GET   /top-selling
section/<id>        GET   /section/<int:id>             → products of a mobile.product.slider
recently_viewed     GET   /recently-viewed               → auth-aware
ask                 POST  /<id>/ask                      → ask-a-question (sets up email)
"""
import logging

from odoo import http
from odoo.http import request

# v2.0.40 — Short-lived per-process cache for the explore feed's full id
# scan. Keyed by the domain tuple; entries expire after 60 s and the cache
# is bounded at ~5 min of writes. Heavy crawler traffic was re-running
# `Tmpl.search(domain).ids` against 1.8k products on every page hit.
_EXPLORE_IDS_CACHE = {}

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner,
    img_url, base_url, get_lang, fmt_price, paginate, bilingual,
)

_logger = logging.getLogger(__name__)


def serialize_product_card(product, lang='en_US'):
    """Compact card shape — used in lists, sliders, recommendations."""
    if not product:
        return None
    cur = product.currency_id or request.env.company.currency_id
    list_price = product.list_price or 0
    compare = product.compare_list_price or 0
    discount = 0
    if compare and compare > list_price:
        discount = int(round((1 - list_price / compare) * 100))
    rating_avg = float(getattr(product, 'rating_avg', 0) or 0)
    rating_count = int(getattr(product, 'rating_count', 0) or 0)
    allow_oos = bool(getattr(product, 'allow_out_of_stock_order', True))
    has_video = bool(getattr(product, 'has_product_video', False)) \
        or bool(getattr(product, 'video_count', 0))
    return {
        'id': product.id,
        'name': bilingual(product, 'name'),
        'slug': product.website_url.rsplit('/', 1)[-1] if product.website_url else f'p-{product.id}',
        'image': img_url('product.template', product.id, 'image_512',
                         unique=product.write_date),
        'price': fmt_price(list_price, cur),
        'compare_price': fmt_price(compare, cur) if compare > 0 else None,
        'discount_pct': discount,
        'currency': cur.name,
        'in_stock': bool(product.qty_available > 0) if product.is_storable else True,
        'qty_available': int(product.qty_available or 0) if product.is_storable else None,
        'allow_out_of_stock_order': allow_oos,
        'rating': {
            'avg': round(rating_avg, 1),
            'count': rating_count,
        },
        'is_published': bool(product.is_published),
        'badges': _product_badges(product),
        'vendor': _vendor_ref(product),
        'has_video': has_video,
    }


def _vendor_ref(product):
    """Compact vendor reference on each product. Returns None when the
    multivendor module isn't installed or the product has no vendor."""
    vendor = getattr(product, 'vendor_id', None)
    if not vendor:
        return None
    return {
        'id':   vendor.id,
        'name': {
            'en': vendor.store_name_en or vendor.display_name or '',
            'ar': vendor.store_name_ar or vendor.store_name_en or vendor.display_name or '',
        },
        'slug': vendor.store_slug or f'v-{vendor.id}',
        'logo': img_url('uellow.vendor', vendor.id, 'logo_image',
                        unique=vendor.write_date) if 'logo_image' in vendor._fields else None,
        'tier': vendor.tier or 'standard',
    }


def _product_badges(product):
    badges = []
    if getattr(product, 'is_new', False):
        badges.append('new')
    if (product.compare_list_price or 0) > (product.list_price or 0):
        badges.append('sale')
    if getattr(product, 'qty_available', 0) <= 0 and product.is_storable:
        badges.append('out_of_stock')
    # v2.0.82 — free-shipping badge surfaced via the new uellow_free_shipping
    # module. `_is_free_shipping` checks product → category → tag in order.
    if hasattr(product, '_is_free_shipping') and product._is_free_shipping():
        badges.append('free_shipping')
    return badges


def serialize_product_full(product, lang='en_US'):
    """Detail-page shape — includes long description, variants, attributes."""
    card = serialize_product_card(product, lang)
    if not card:
        return None
    # Long description (jsonb-translated). v2.0.77 — read the actual
    # fields Odoo's product form writes to. `description_ecommerce` is the
    # website e-commerce body editor (the rich block-editor the admin
    # uses); `description_sale` is the order-line snippet;
    # `website_description` is a legacy/duplicate field on some installs.
    # Fall back through all three so admins can put the long body in
    # whichever editor they're using.
    def _firstNonEmpty(*candidates):
        for c in candidates:
            if c and (c.get('en') or c.get('ar')):
                return c
        return {'en': '', 'ar': ''}
    public_desc = _firstNonEmpty(
        bilingual(product, 'description_ecommerce')
            if 'description_ecommerce' in product._fields else None,
        bilingual(product, 'website_description'),
    )
    desc = _firstNonEmpty(
        bilingual(product, 'description_sale'),
        public_desc,
    )

    # Variant attributes — for color, try to pull the matching variant's
    # image instead of the attribute-value swatch (so we show the actual
    # product photo in that color, not a flat color square)
    attribute_lines = []
    for line in product.attribute_line_ids:
        is_color_attr = 'color' in (line.attribute_id.name or '').lower() \
                       or 'لون' in (line.attribute_id.name or '')
        values = []
        for v in line.value_ids:
            value_image = None
            if is_color_attr:
                # Find variant that has this value
                matching = product.product_variant_ids.filtered(
                    lambda pv: v.id in pv.product_template_attribute_value_ids
                        .mapped('product_attribute_value_id').ids)
                if matching and matching[0].image_512:
                    value_image = img_url('product.product', matching[0].id,
                                          'image_512',
                                          unique=matching[0].write_date)
            if not value_image and v.image:
                value_image = img_url('product.attribute.value', v.id,
                                      'image', unique=v.write_date)
            values.append({
                'id': v.id,
                'name': bilingual(v, 'name'),
                'html_color': v.html_color or '',
                'image': value_image,
            })
        attribute_lines.append({
            'attribute_id': line.attribute_id.id,
            'attribute_name': bilingual(line.attribute_id, 'name'),
            'display_type': line.attribute_id.display_type,
            'values': values,
        })

    # Gallery
    images = [img_url('product.template', product.id, 'image_1024',
                      unique=product.write_date)]
    for img in product.product_template_image_ids[:20]:
        images.append(img_url('product.image', img.id, 'image_1024',
                              unique=img.write_date))

    # Categories + brand
    public_categs = [{
        'id': c.id,
        'name': bilingual(c, 'name'),
    } for c in product.public_categ_ids]

    # All-time sold count from confirmed sale order lines.
    sold_count = 0
    try:
        Sol = request.env['sale.order.line'].sudo()
        rows = Sol.read_group(
            domain=[
                ('product_id.product_tmpl_id', '=', product.id),
                ('order_id.state', 'in', ['sale', 'done']),
            ],
            fields=['product_uom_qty:sum'], groupby=[],
        )
        sold_count = int(rows[0]['product_uom_qty'] or 0) if rows else 0
    except Exception:
        sold_count = 0

    # Real view count from website.track
    view_count = product._get_product_view_safe() if hasattr(product, '_get_product_view_safe') else 0

    # Brand — three-tier resolution:
    #   1. product.brand_id (logo on the dedicated brand record)
    #   2. Brand attribute value (its own image, OR — if not set — fall back
    #      to a product.brand record whose name matches the attribute value)
    #   3. Attribute value name only (text, no logo)
    brand = None
    pb = getattr(product, 'brand_id', False)
    if pb:
        has_img = bool(getattr(pb, 'image_1024', False))
        brand = {
            'id': pb.id,
            'name': {'en': pb.name or '', 'ar': pb.name or ''},
            'image': img_url('product.brand', pb.id, 'image_1024',
                             unique=pb.write_date) if has_img else None,
        }
    if brand is None or not brand.get('image'):
        for line in product.attribute_line_ids:
            n = (line.attribute_id.name or '').lower()
            if 'brand' in n or 'ماركة' in n or 'علامة' in n:
                v = line.value_ids[:1]
                if v:
                    img = None
                    # v2.0.77 — try the binary fields actually populated in
                    # this database. `dr_image` is the field used by the
                    # `dr_*` brand module (logos are stored on the attribute
                    # value via ir.attachment with res_field='dr_image').
                    # Fall back to the standard `image` field for installs
                    # that use it.
                    for fld in ('dr_image', 'image'):
                        if fld in v._fields and v[fld]:
                            img = img_url('product.attribute.value', v.id, fld,
                                          unique=v.write_date)
                            break
                    # If still none, try matching a product.brand record by
                    # name (case + space insensitive).
                    if not img:
                        vname = (v.name or '').strip()
                        if vname:
                            cmp = vname.lower().replace(' ', '').replace('-', '')
                            for pbrec in request.env['product.brand'].sudo().search([]):
                                pn = (pbrec.name or '').lower().replace(' ', '').replace('-', '')
                                if pn and pn == cmp and getattr(pbrec, 'image_1024', False):
                                    img = img_url('product.brand', pbrec.id,
                                                  'image_1024', unique=pbrec.write_date)
                                    break
                    brand = brand or {
                        'id': v.id,
                        'name': bilingual(v, 'name'),
                        'image': None,
                    }
                    if img:
                        brand['image'] = img
                break

    # Bulk pricing — read from pricelist
    bulk_tiers = _bulk_pricing_tiers(product)

    # Continue-selling: hide the Notify-me CTA & treat as available
    allow_oos = bool(getattr(product, 'allow_out_of_stock_order', True))

    # Active flash sale (if any) — surface ends_at so the product page
    # can render the same FlashBanner widget.
    flash_sale = None
    try:
        Sale = request.env['mobile.flash.sale'].sudo()
        sales = Sale.search([('active', '=', True)])
        for s in sales:
            if not s.is_live:
                continue
            in_sale = product in s._resolved_products()
            if in_sale:
                flash_sale = {
                    'id': s.id,
                    'title': {'en': s.name or '', 'ar': s.name_ar or s.name or ''},
                    'end_date': s.end_date and s.end_date.isoformat() or None,
                }
                break
    except Exception:
        flash_sale = None

    # Product videos — from uellow_tiktok_video product.video records.
    videos = _serialize_product_videos(product)
    return {
        **card,
        'flash_sale': flash_sale,
        'description_short': desc,
        'description_html': public_desc,
        'images': images,
        'videos': videos,
        'has_video': bool(videos),
        'attributes': attribute_lines,
        'categories': public_categs,
        'sku':   product.default_code or '',
        'barcode': product.barcode or '',
        'sold_count': sold_count,
        'view_count': view_count,
        'brand': brand,
        'bulk_pricing': bulk_tiers,
        # v2.0.58: effective max purchasable quantity for this product
        # (resolution order: product override → category → global default).
        # Mobile uses this to cap the +/- quantity selector.
        'max_qty_buyable': request.env['uellow.bulk.pricing.config']
                              .sudo().max_qty_for(product),
        'allow_out_of_stock_order': allow_oos,
        # Only return warranty when the product actually has the field set;
        # otherwise None so the UI hides the row instead of showing a fake 12.
        'warranty_months': (int(getattr(product, 'warranty_months', 0) or 0)
                            if 'warranty_months' in product._fields
                            and product.warranty_months else None),
        'shipping_info_label': {
            'en': 'Standard delivery 1-3 days',
            'ar': 'توصيل قياسي 1-3 أيام',
        },
    }


def _serialize_product_videos(product):
    """Pull product.video rows tied to this template. Each video returns
    {type, title, embed_url, file_url, thumbnail_url, mime} so the app
    can render them in the gallery alongside images."""
    out = []
    try:
        if 'video_ids' not in product._fields and 'product_video_ids' not in product._fields:
            return out
        videos = getattr(product, 'video_ids', None) or getattr(product, 'product_video_ids', None)
        if not videos:
            return out
        for v in videos.filtered(lambda x: x.active):
            item = {
                'id': v.id,
                'title': v.name or '',
                'type': v.video_type or 'youtube',
                'embed_url': v.embed_url or '',
                'tiktok_url': v.tiktok_url or '',
                'tiktok_video_id': v.tiktok_video_id or '',
                'video_url': v.video_url or '',
                'thumbnail': (img_url('product.video', v.id, 'thumbnail',
                                      unique=v.write_date) if v.thumbnail else None),
            }
            if v.video_type == 'direct_upload' and v.video_file:
                fname = (v.video_filename or 'video.mp4').replace('/', '-')
                item['file_url'] = f'/web/content/product.video/{v.id}/video_file/{fname}'
                item['mime'] = v.video_mimetype or 'video/mp4'
            out.append(item)
    except Exception:
        return []
    return out


def _domain_published_for_app(include_oos=False):
    """Use this on every public-facing query — keeps unpublished /
    archived items out of the app and only shows what's available
    on the active website (or website-agnostic products).

    When `include_oos=False` (default for listings) products that are
    out of stock AND don't allow backorder are excluded. Search calls
    pass `include_oos=True` so users can still find an OOS item if
    they ask for it explicitly."""
    website = request.env['website'].sudo().search([], limit=1)
    base = [
        ('is_published', '=', True),
        ('active', '=', True),
        '|', ('website_id', '=', False), ('website_id', '=', website.id),
    ]
    if not include_oos:
        # Show storable items that have qty > 0 OR allow backorder,
        # plus all non-storable items (services, etc.).
        base += [
            '|',
                ('is_storable', '=', False),
                '|',
                    ('allow_out_of_stock_order', '=', True),
                    ('qty_available', '>', 0),
        ]
    return base


class MobileProductsAPI(http.Controller):

    # ─── List products with filters ───────────────────────────────────
    @http.route('/api/mobile/v2/products', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_products(self, **kw):
        p = get_payload()
        lang = get_lang()
        domain = _domain_published_for_app()

        # Category filter (via public_categ_ids)
        if p.get('category_id'):
            try:
                domain.append(('public_categ_ids', 'child_of', int(p['category_id'])))
            except Exception:
                pass

        # Search query — search across name + description
        search = (p.get('search') or p.get('q') or '').strip()
        if search:
            domain += ['|', ('name', 'ilike', search),
                            ('description_sale', 'ilike', search)]

        # Brand filter
        if p.get('brand_id'):
            try:
                domain.append(('attribute_line_ids.value_ids', 'in', [int(p['brand_id'])]))
            except Exception:
                pass

        # Generic attribute-value filter — comma-separated IDs from the
        # /filters endpoint. Each ID becomes an OR'd constraint inside a
        # single domain leaf (AND across distinct attributes is handled
        # client-side for now: the client posts the union of selections).
        val_csv = (p.get('value_ids') or '').strip()
        if val_csv:
            try:
                ids = [int(x) for x in val_csv.split(',') if x.strip().isdigit()]
                if ids:
                    domain.append(('attribute_line_ids.value_ids', 'in', ids))
            except Exception:
                pass

        # Tag filter
        if p.get('tag_id'):
            try:
                domain.append(('product_tag_ids', 'in', [int(p['tag_id'])]))
            except Exception:
                pass

        # Price range
        try:
            if p.get('min_price'):
                domain.append(('list_price', '>=', float(p['min_price'])))
            if p.get('max_price'):
                domain.append(('list_price', '<=', float(p['max_price'])))
        except Exception:
            pass

        # On-sale only
        if p.get('on_sale') in ('1', 'true', True):
            domain.append(('compare_list_price', '>', 0))

        # v2.0.80 — minimum rating filter (4 = "4★ & up"). Only applied
        # when the product.template has a `rating_avg` aggregate.
        try:
            mr = float(p.get('min_rating') or 0)
            if mr > 0 and 'rating_avg' in request.env['product.template']._fields:
                domain.append(('rating_avg', '>=', mr))
        except Exception:
            pass

        # Sort
        sort_map = {
            'newest':       'create_date desc',
            'oldest':       'create_date asc',
            'price_asc':    'list_price asc',
            'price_desc':   'list_price desc',
            'name':         'name asc',
            'popular':      'sales_count desc' if 'sales_count' in request.env['product.template']._fields else 'create_date desc',
            'top_rated':    'rating_avg desc' if 'rating_avg' in request.env['product.template']._fields else 'create_date desc',
        }
        order = sort_map.get(p.get('sort', 'newest'), 'create_date desc')

        Tmpl = request.env['product.template'].sudo()
        all_recs = Tmpl.search(domain, order=order)
        items, meta = paginate(
            all_recs,
            page=p.get('page', 1),
            per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )
        return ok(items, meta)

    # ─── Brand info (header + product list) ───────────────────────────
    @http.route('/api/mobile/v2/products/brand/<int:value_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def brand_detail(self, value_id, **kw):
        """Return brand summary + first page of products for that brand
        attribute value. Used by the brand store page in the app."""
        p = get_payload()
        lang = get_lang()
        Val = request.env['product.attribute.value'].sudo()
        v = Val.browse(value_id)
        if not v.exists():
            return fail('NOT_FOUND', 'Brand not found', 404)

        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app() + [
            ('attribute_line_ids.value_ids', 'in', [value_id]),
        ]
        records = Tmpl.search(domain, order='create_date desc')
        items, meta = paginate(
            records,
            page=p.get('page', 1),
            per_page=p.get('per_page', 20),
            serializer=lambda r: serialize_product_card(r, lang),
        )
        return ok({
            'brand': {
                'id': v.id,
                'name': bilingual(v, 'name'),
                'image': img_url('product.attribute.value', v.id, 'image',
                                 unique=v.write_date) if v.image else None,
                'total_products': len(records),
            },
            'products': items,
        }, meta)

    # ─── Explore (random infinite) ────────────────────────────────────
    @http.route('/api/mobile/v2/products/explore', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def explore_products(self, **kw):
        """Lightweight randomized feed for the Explore More section on
        home. Uses a deterministic pseudo-random key based on (date,
        seed) so a single user's scroll feels random but the same SQL
        plan executes repeatedly — server-friendly. Pagination is by
        an integer cursor; same cursor → same page → safe to cache."""
        p = get_payload()
        lang = get_lang()
        try:
            seed = int(p.get('seed') or 0) or 1
            page = int(p.get('page') or 1)
            per_page = int(p.get('per_page') or 12)
        except Exception:
            return fail('BAD_REQUEST', 'Invalid seed/page')
        per_page = max(1, min(per_page, 40))

        domain = _domain_published_for_app()
        # v2.0.37 — accept narrowing: ?category_id=…&sort=…
        cat_id = p.get('category_id')
        if cat_id:
            try:
                domain = domain + [('public_categ_ids', 'in', [int(cat_id)])]
            except Exception:
                pass
        sort = (p.get('sort') or 'best_match').strip()

        Tmpl = request.env['product.template'].sudo()
        order_map = {
            'newest':     'create_date desc',
            'price_asc':  'list_price asc',
            'price_desc': 'list_price desc',
            'top_rated':  'write_date desc',
        }
        if sort in order_map:
            recs = Tmpl.search(domain, order=order_map[sort], limit=per_page,
                               offset=(page - 1) * per_page)
            total = Tmpl.search_count(domain)
            has_next = (page * per_page) < total
            items_raw = recs
        else:
            # Random — deterministic with seed. Cache the full id list for
            # 60 s so heavy crawler/bot traffic doesn't re-scan the whole
            # product table on every page request (v2.0.40 perf fix).
            import time as _t
            # Domain may contain lists/tuples; freeze to a hashable shape
            def _freeze(d):
                if isinstance(d, (list, tuple)):
                    return tuple(_freeze(x) for x in d)
                return d
            _cache_key = _freeze(domain)
            now = _t.time()
            cached = _EXPLORE_IDS_CACHE.get(_cache_key)
            if cached and now - cached[1] < 60:
                all_ids = list(cached[0])
            else:
                all_ids = Tmpl.search(domain).ids
                _EXPLORE_IDS_CACHE[_cache_key] = (tuple(all_ids), now)
                # Bound the cache — drop entries older than 5 minutes
                stale = [k for k, v in _EXPLORE_IDS_CACHE.items() if now - v[1] > 300]
                for k in stale: _EXPLORE_IDS_CACHE.pop(k, None)
            if not all_ids:
                return ok([], {'page': page, 'per_page': per_page, 'has_next': False,
                               'total': 0, 'seed': seed})
            import hashlib
            def _key(pid):
                h = hashlib.md5(f'{seed}:{pid}'.encode()).digest()
                return int.from_bytes(h[:8], 'big')
            all_ids.sort(key=_key)
            total = len(all_ids)
            start = (page - 1) * per_page
            chunk = all_ids[start:start + per_page]
            has_next = (start + per_page) < total
            items_raw = Tmpl.browse(chunk).sorted(key=lambda r: chunk.index(r.id))

        items = [serialize_product_card(r, lang) for r in items_raw]
        # Enrich with discovery badges (matching what the resolver does).
        # Pre-fetch the free-ship threshold ONCE per request so the inner
        # loop doesn't do per-product DB lookups (v2.0.40 perf fix).
        try:
            from odoo.addons.uellow_mobile_pages.models.block_resolver import (
                _enrich_with_badges, _get_free_ship_threshold,
            )
            free_ship_thr = _get_free_ship_threshold(request.env)
            for it, rec in zip(items, items_raw):
                _enrich_with_badges(request.env, it, rec,
                                    free_ship_threshold=free_ship_thr)
        except Exception:
            pass
        return ok(items, {
            'page': page, 'per_page': per_page,
            'has_next': has_next, 'total': total, 'seed': seed,
        })

    # ─── Product detail ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/products/<int:product_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def product_detail(self, product_id, **kw):
        lang = get_lang()
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists() or not product.is_published:
            return fail('NOT_FOUND', 'Product not found', 404)
        return ok({'product': serialize_product_full(product, lang)})

    # ─── Variants ─────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/products/<int:product_id>/variants', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def variants(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        items = []
        for v in product.product_variant_ids:
            cur = v.currency_id or request.env.company.currency_id
            items.append({
                'id': v.id,
                'sku': v.default_code or '',
                'barcode': v.barcode or '',
                'price': fmt_price(v.lst_price or 0, cur),
                'qty_available': int(v.qty_available or 0) if v.is_storable else None,
                'in_stock': bool(v.qty_available > 0) if v.is_storable else True,
                'image': img_url('product.product', v.id, 'image_512',
                                 unique=v.write_date),
                'attributes': [{
                    'attribute_id': ptav.attribute_id.id,
                    'value_id': ptav.product_attribute_value_id.id,
                    'value_name': bilingual(ptav.product_attribute_value_id, 'name'),
                } for ptav in v.product_template_attribute_value_ids],
            })
        return ok({'variants': items})

    # ─── Reviews summary (with images + breakdown) ────────────────────
    @http.route('/api/mobile/v2/products/<int:product_id>/reviews', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def reviews(self, product_id, **kw):
        p = get_payload()
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)

        Review = request.env.get('product.review')
        items = []
        meta = {'page': 1, 'per_page': 20, 'total': 0}
        breakdown = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        if Review is not None:
            try:
                recs = Review.sudo().search([
                    ('product_id', '=', product.id),
                    ('state', '=', 'approved'),
                ], order='create_date desc')
                # Star breakdown
                for r in recs:
                    rating = int(r.rating or 0)
                    if 1 <= rating <= 5:
                        breakdown[str(rating)] = breakdown.get(str(rating), 0) + 1
                items, meta = paginate(
                    recs,
                    page=p.get('page', 1),
                    per_page=p.get('per_page', 20),
                    serializer=_serialize_review,
                )
            except Exception:
                pass
        return ok({
            'reviews': items,
            'summary': {
                'avg': round(float(getattr(product, 'rating_avg', 0) or 0), 1),
                'total': int(getattr(product, 'rating_count', 0) or 0),
                'breakdown': breakdown,
            },
        }, meta)

    # ─── Reviewers (expert reviewers attached to this product) ────────
    @http.route('/api/mobile/v2/products/<int:product_id>/reviewers', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def reviewers(self, product_id, **kw):
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        Profile = request.env.get('reviewer.profile')
        if Profile is None:
            return ok({'enabled': False, 'reviewers': []})

        # Show online + verified reviewers, ranked by level + rating
        reviewers = Profile.sudo().search([
            ('state', '=', 'active'),
        ], order='is_online desc, rating desc, review_count desc', limit=8)
        return ok({
            'enabled': True,
            'count': len(reviewers),
            'reviewers': [_serialize_reviewer(r) for r in reviewers],
        })

    # ─── Related ──────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/products/<int:product_id>/related', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def related(self, product_id, **kw):
        lang = get_lang()
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        # Same public category
        categ_ids = product.public_categ_ids.ids
        domain = _domain_published_for_app() + [
            ('id', '!=', product.id),
            ('public_categ_ids', 'in', categ_ids),
        ]
        items = request.env['product.template'].sudo().search(
            domain, order='create_date desc', limit=12)
        return ok([serialize_product_card(p, lang) for p in items])

    # ─── Top selling ──────────────────────────────────────────────────
    @http.route('/api/mobile/v2/products/top-selling', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def top_selling(self, **kw):
        lang = get_lang()
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app()
        order_field = 'sales_count desc' if 'sales_count' in Tmpl._fields else 'create_date desc'
        items = Tmpl.search(domain, order=order_field, limit=20)
        return ok([serialize_product_card(p, lang) for p in items])

    # ─── Recommended (personalised when logged in) ────────────────────
    @http.route('/api/mobile/v2/products/recommended', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def recommended(self, **kw):
        lang = get_lang()
        partner = current_partner()
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app()
        if partner:
            # Categories the user has previously ordered from.
            sale_lines = request.env['sale.order.line'].sudo().search([
                ('order_id.partner_id', '=', partner.id),
                ('order_id.state', 'in', ['sale', 'done']),
            ], limit=80)
            categ_ids = sale_lines.product_id.mapped('product_tmpl_id.public_categ_ids').ids
            if categ_ids:
                domain.append(('public_categ_ids', 'in', categ_ids))
        items = Tmpl.search(domain, order='create_date desc', limit=20)
        return ok([serialize_product_card(p, lang) for p in items])

    # ─── Recently viewed (auth required) ──────────────────────────────
    @http.route('/api/mobile/v2/products/recently-viewed', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def recently_viewed(self, **kw):
        partner = current_partner()
        if not partner:
            return ok([])
        lang = get_lang()
        # Use website.track if available, otherwise empty list.
        Track = request.env.get('website.track')
        if Track is None:
            return ok([])
        visitor = request.env['website.visitor'].sudo().search([
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not visitor:
            return ok([])
        recent = Track.sudo().search([
            ('visitor_id', '=', visitor.id),
            ('product_id', '!=', False),
        ], order='visit_datetime desc', limit=20)
        tmpl_ids = recent.mapped('product_id.product_tmpl_id').ids
        seen = set()
        unique = []
        for tid in tmpl_ids:
            if tid not in seen:
                seen.add(tid)
                unique.append(tid)
        templates = request.env['product.template'].sudo().browse(unique).exists()
        return ok([serialize_product_card(p, lang) for p in templates])

    # ─── Section products (from mobile.product.slider) ────────────────
    @http.route('/api/mobile/v2/products/section/<int:section_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def section_products(self, section_id, **kw):
        lang = get_lang()
        section = request.env['mobile.product.slider'].sudo().browse(section_id)
        if not section.exists():
            return fail('NOT_FOUND', 'Section not found', 404)
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app()

        st = section.section_type
        if st == 'manual' and section.product_ids:
            items = section.product_ids.filtered(lambda p: p.is_published and p.active)
        elif st == 'category' and section.category_id:
            domain.append(('public_categ_ids', 'child_of', section.category_id.id))
            items = Tmpl.search(domain, limit=section.max_products or 20,
                                order='create_date desc')
        elif st == 'brand' and getattr(section, 'brand_attribute_value_id', False):
            domain.append(('attribute_line_ids.value_ids', 'in',
                           [section.brand_attribute_value_id.id]))
            items = Tmpl.search(domain, limit=section.max_products or 20,
                                order='create_date desc')
        elif st == 'tag' and section.product_tag_id:
            domain.append(('product_tag_ids', 'in', [section.product_tag_id.id]))
            items = Tmpl.search(domain, limit=section.max_products or 20,
                                order='create_date desc')
        elif st == 'new':
            items = Tmpl.search(domain, limit=section.max_products or 20,
                                order='create_date desc')
        elif st == 'top':
            order_field = 'sales_count desc' if 'sales_count' in Tmpl._fields else 'create_date desc'
            items = Tmpl.search(domain, limit=section.max_products or 20,
                                order=order_field)
        elif st == 'sale':
            domain.append(('compare_list_price', '>', 0))
            items = Tmpl.search(domain, limit=section.max_products or 20)
        else:
            items = Tmpl.browse([])

        return ok([serialize_product_card(p, lang) for p in items])

    # ─── Ask a question about a product ───────────────────────────────
    @http.route('/api/mobile/v2/products/<int:product_id>/ask', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def ask(self, product_id, **kw):
        p = get_payload()
        question = (p.get('question') or '').strip()
        contact_email = (p.get('email') or '').strip()
        partner = current_partner()
        if not question:
            return fail('MISSING_QUESTION', 'Question required')
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)

        # Persist a mail.message on the product record so the team sees it.
        try:
            product.message_post(
                body=f"Mobile question on '{product.name}':\n{question}\n\n"
                     f"From: {partner.email if partner else contact_email or 'guest'}",
                subject=f"App question — {product.name}",
            )
        except Exception:
            pass
        return ok({'sent': True})


# ─── Review + Reviewer serializers ────────────────────────────────────

def _serialize_review(r):
    """Single review with photos + verified-purchase + helpful count."""
    photos = []
    if 'photo_ids' in r._fields:
        for att in r.photo_ids:
            photos.append(img_url('ir.attachment', att.id, 'datas',
                                  unique=att.write_date) if att.datas else None)
        photos = [p for p in photos if p]
    return {
        'id':     r.id,
        'rating': int(r.rating or 0),
        'title':  r.title or '',
        'body':   r.body or '',
        'author': r.partner_id.name if r.partner_id else 'Anonymous',
        'avatar': img_url('res.partner', r.partner_id.id, 'image_128',
                          unique=r.partner_id.write_date) if r.partner_id else None,
        'date':   r.create_date.isoformat() if r.create_date else None,
        'verified_purchase': bool(getattr(r, 'is_verified', False)),
        'helpful_count': int(getattr(r, 'helpful_count', 0) or 0),
        'photos': photos,
        'video_url': getattr(r, 'video_url', '') or '',
        'vendor_reply': getattr(r, 'vendor_reply', '') or '',
    }


def _serialize_reviewer(r):
    """Expert reviewer profile (uellow_reviewers module)."""
    return {
        'id':         r.id,
        'name':       r.display_name or '',
        'bio':        r.bio or '',
        'avatar':     img_url('reviewer.profile', r.id, 'avatar',
                              unique=r.write_date) if r.avatar else None,
        'level':      r.level or 'starter',
        'is_online':  bool(r.is_online),
        'verified':   bool(r.verified),
        'verified_purchase': bool(r.verified_purchase),
        'review_count':  int(r.review_count or 0),
        'rating':       round(float(r.rating or 0), 1),
        'conversion_rate': round(float(r.conversion_rate or 0), 1),
        'allow_written': bool(r.allow_written),
        'allow_chat':    bool(r.allow_chat),
        'price_written': float(r.price_written or 0),
        'price_chat':    float(r.price_chat or 0),
        'specialty':     r.specialty_text or '',
    }


def _bulk_pricing_tiers(product):
    """Read bulk-pricing tiers for this product from the *active website's*
    pricelist. Scoped properly so each country/website ladder applies."""
    list_p = float(product.list_price or 0)
    cur = product.currency_id
    sym = cur.symbol if cur else 'KD'
    tiers = []

    # Resolve the right pricelist for the current website (country).
    pricelist = None
    try:
        website = request.env['website'].sudo().search([], limit=1)
        if website:
            # Odoo 18 stores the website pricelist on website.pricelist_id
            pricelist = getattr(website, 'pricelist_id', None) \
                or website._get_current_pricelist() \
                  if hasattr(website, '_get_current_pricelist') else None
    except Exception:
        pricelist = None

    try:
        Item = request.env['product.pricelist.item'].sudo()
        # Tier items for this product/template, scoped to website pricelist
        # if one is configured — falls back to "any pricelist" if not.
        base_domain = [
            '|', ('product_tmpl_id', '=', product.id),
                 ('product_id.product_tmpl_id', '=', product.id),
            ('min_quantity', '>', 1),
        ]
        if pricelist:
            base_domain.append(('pricelist_id', '=', pricelist.id))
        items = Item.search(base_domain, order='min_quantity asc', limit=5)
        # If we found nothing scoped to the website pricelist, fall back to
        # global ladder items (no pricelist) but still tied to this product.
        if not items and pricelist:
            items = Item.search([
                '|', ('product_tmpl_id', '=', product.id),
                     ('product_id.product_tmpl_id', '=', product.id),
                ('min_quantity', '>', 1),
            ], order='min_quantity asc', limit=5)

        variant = product.product_variant_ids[:1]
        for it in items:
            try:
                price = it._compute_price(
                    variant, it.min_quantity,
                    request.env.user.partner_id,
                ) if hasattr(it, '_compute_price') else (it.fixed_price or list_p)
            except Exception:
                price = it.fixed_price or list_p
            tiers.append({
                'min_qty': int(it.min_quantity),
                'price': round(float(price), 3),
                'currency': sym,
                'save_pct': int(round((1 - price/list_p) * 100)) if list_p > 0 else 0,
            })
    except Exception:
        pass

    # ── v2.0.57: route through uellow.bulk.pricing.config for exclusions,
    # cost-floor protection, max-tier cap, and auto-generated tiers when
    # the pricelist is empty.
    try:
        Cfg = request.env['uellow.bulk.pricing.config'].sudo()
        cfg = Cfg.get_config()
        # Guest-visibility gate
        if not cfg.show_to_guest and request.env.user._is_public():
            return []
        # Pass the raw pricelist tiers through the rules engine
        raw_items = [{'min_quantity': t['min_qty'], 'price': t['price']}
                     for t in tiers]
        tiers = Cfg.build_tiers(product, pricelist_items=raw_items,
                                list_price=list_p, currency_sym=sym)
    except Exception:
        # Fail-safe: if the engine errors, fall back to the basic list above
        # capped at 4 and with no floor enforcement.
        tiers = tiers[:4]

    if not tiers:
        return []
    # Always prepend the "1+ pcs" base tier so the UI shows the
    # comparison strip cleanly.
    if tiers and tiers[0].get('min_qty', 0) > 1:
        tiers.insert(0, {
            'min_qty': 1, 'price': round(list_p, 3),
            'currency': sym, 'save_pct': 0, 'capped': False,
        })
    return tiers
