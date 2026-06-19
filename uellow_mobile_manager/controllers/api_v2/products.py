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
    img_url, base_url, get_lang, fmt_price, paginate, bilingual, get_website,
    brand_value_logo, is_brand_attribute,
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
    # v2.2.48 — promotions engine: apply the active MOBILE promo discount at
    # COMPUTE time (channel-isolated) so the app shows the reduced price +
    # struck original WITHOUT writing list_price (which would hit the website
    # too). Skipped when the product is already on sale (compare > price), to
    # avoid double-discounting. The promo's discount_pct is already
    # margin-guarded when the line was generated.
    if not (compare and compare > list_price):
        try:
            _coin = _promo_badge(product)
            _d = float((_coin or {}).get('discount_pct') or 0.0)
            if _d > 0 and list_price > 0:
                compare = list_price
                list_price = round(list_price * (1 - _d / 100.0), 3)
                discount = int(round(_d))
        except Exception:
            pass
    rating_avg = float(getattr(product, 'rating_avg', 0) or 0)
    rating_count = int(getattr(product, 'rating_count', 0) or 0)
    allow_oos = bool(getattr(product, 'allow_out_of_stock_order', True))
    has_video = bool(getattr(product, 'has_product_video', False)) \
        or bool(getattr(product, 'video_count', 0))
    return {
        'id': product.id,
        'name': bilingual(product, 'name'),
        'slug': product.website_url.rsplit('/', 1)[-1] if product.website_url else f'p-{product.id}',
        # v2.2.33 — card grids use image_512 (256 looked soft/low-quality on
        # 2x/3x phone screens). The product page still uses image_1024/1920.
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
        'rank': _product_rank_badge(product),
        'price_trend': _price_trend(product),
        'cart_adds': _cart_adds_count(product),
        'promo': _promo_badge(product),
    }



# ─── v2.1.48 — card-enrichment cache ─────────────────────────────────
# rank / promo / cart-adds / price-trend each cost a query PER PRODUCT;
# a builder home with ~60 cards fired 200+ queries per request and the
# app start felt heavy. These signals change slowly, so a short
# worker-local TTL cache amortizes them across users and requests.
import time as _time

_CARD_CACHE = {}


def _card_cached(kind, key, ttl, fn):
    now = _time.time()
    hit = _CARD_CACHE.get((kind, key))
    if hit is not None and now - hit[1] < ttl:
        return hit[0]
    val = fn()
    _CARD_CACHE[(kind, key)] = (val, now)
    if len(_CARD_CACHE) > 12000:        # bound worker memory
        for k in sorted(_CARD_CACHE, key=lambda k: _CARD_CACHE[k][1])[:6000]:
            _CARD_CACHE.pop(k, None)
    return val


def _product_rank_badge(product):
    return _card_cached('rank', (product.id, get_website().id),
                        600, lambda: _rank_badge_uncached(product))


def _rank_badge_uncached(product):
    """v2.1.24 — best 'Best Seller #N in <category>' badge for cards.
    Only ranks ≤ badge_max_rank show on cards; None when unranked."""
    try:
        Rank = request.env.get('uellow.product.rank')
        if Rank is None:
            return None
        cfg = request.env['uellow.rank.config'].sudo().get_config()
        if not cfg.enabled:
            return None
        r = Rank.sudo().best_for(product.id, website_id=get_website().id)
        if not r or r.rank > max(1, cfg.badge_max_rank):
            return None
        return _rank_dict(r)
    except Exception:
        return None


def _promo_badge(product):
    return _card_cached('promo', (product.id, get_website().id),
                        120, lambda: _promo_badge_uncached(product))


def _promo_badge_uncached(product):
    """v2.1.30 — active promotion coin for this product (or None)."""
    try:
        Promo = request.env.get('mobile.app.promotion')
        if Promo is None:
            return None
        return Promo.sudo().badge_for(product.id,
                                      website_id=get_website().id)
    except Exception:
        _logger.exception('promo badge_for failed for product %s',
                          product.id)
        return None


def _cart_adds_count(product):
    return _card_cached('cart_adds', product.id,
                        900, lambda: _cart_adds_uncached(product))


def _cart_adds_uncached(product):
    """v2.1.30 — how many carts the product was added to (30 days,
    any order state — social proof for the card ticker)."""
    try:
        request.env.cr.execute("""
            SELECT COUNT(DISTINCT sol.order_id)
              FROM sale_order_line sol
              JOIN product_product pp ON pp.id = sol.product_id
              JOIN sale_order so ON so.id = sol.order_id
             WHERE pp.product_tmpl_id = %s
               AND so.date_order >= (NOW() - INTERVAL '30 days')
        """, [product.id])
        return int(request.env.cr.fetchone()[0] or 0)
    except Exception:
        return 0


def _price_trend(product):
    return _card_cached('trend', product.id,
                        600, lambda: _price_trend_uncached(product))


def _price_trend_uncached(product):
    """v2.1.25 — internal price-intelligence indicator for cards.
    {'direction','change_pct','is_lowest','label{en,ar}'} or None."""
    try:
        Hist = request.env.get('uellow.price.history')
        if Hist is None:
            return None
        t = Hist.sudo().trend_for(product.id)
        if not t:
            return None
        if t['is_lowest']:
            # v2.1.59 — short label so it never wraps on the card line.
            label = {'en': 'Lowest price ✓', 'ar': 'أقل سعر ✓'}
        elif t['direction'] == 'down':
            label = {'en': 'Price dropped %s%%' % t['change_pct'],
                     'ar': 'انخفض السعر %s%%' % t['change_pct']}
        elif t['direction'] == 'up':
            label = {'en': 'Price up %s%%' % t['change_pct'],
                     'ar': 'ارتفع السعر %s%%' % t['change_pct']}
        else:
            label = {'en': 'Stable price', 'ar': 'سعر مستقر'}
        return {**t, 'label': label}
    except Exception:
        return None


def _rank_dict(r):
    cat = bilingual(r.category_id, 'name')
    if r.rank == 1:
        label = {'en': 'Best Seller in %s' % (cat.get('en') or ''),
                 'ar': 'الأفضل مبيعاً في %s' % (cat.get('ar') or cat.get('en') or '')}
    else:
        label = {'en': '#%s Best Seller in %s' % (r.rank, cat.get('en') or ''),
                 'ar': '#%s الأكثر مبيعاً في %s' % (r.rank, cat.get('ar') or cat.get('en') or '')}
    return {
        'rank': r.rank,
        'category_id': r.category_id.id,
        'category': cat,
        'label': label,
    }


def _top_selling_ids(domain, limit=200):
    """Product ids ranked by REAL sold quantity (sale.report aggregate),
    then the rest of the domain as filler. product.template.sales_count
    is a NON-STORED compute — using it as a search order raises
    'Cannot convert ... to SQL' (v2.1.66 fix)."""
    Tmpl = request.env['product.template'].sudo()
    base_ids = Tmpl.search(domain, limit=1000).ids
    if not base_ids:
        return []
    ranked = []
    try:
        groups = request.env['sale.report'].sudo().read_group(
            [('product_tmpl_id', 'in', base_ids),
             ('state', 'in', ('sale', 'done'))],
            ['product_uom_qty'], ['product_tmpl_id'],
            orderby='product_uom_qty desc', limit=limit)
        ranked = [g['product_tmpl_id'][0] for g in groups
                  if g.get('product_tmpl_id')]
    except Exception:
        ranked = []
    seen = set(ranked)
    return (ranked + [i for i in base_ids if i not in seen])[:limit]


# House fallback shown when a product has no vendor, or the vendor opted to
# hide its name. Rendered by the app as the yellow "Uellow Vendors" bar.
UELLOW_VENDORS_REF = {
    'id':    0,
    'name':  {'en': 'Uellow Vendors', 'ar': 'تجار يلو'},
    'slug':  'uellow-vendors',
    'logo':  None,
    'tier':  'standard',
    'house': True,
}


def _vendor_ref(product):
    """Compact vendor reference on each product. Always returns a ref: a real
    vendor when set and it allows showing its name, otherwise the house
    "Uellow Vendors" fallback (anonymous vendor or no vendor)."""
    vendor = getattr(product, 'vendor_id', None)
    if not vendor:
        return dict(UELLOW_VENDORS_REF)
    # respect the vendor's "Show Vendor Name on Product" setting
    settings = getattr(vendor, 'settings_id', None)
    if settings and not settings.show_vendor_name:
        return dict(UELLOW_VENDORS_REF)
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
        'house': False,
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
    # v2.2.20 — bundle badge so cards can flag "Bundle / باقة".
    if getattr(product, 'is_bundle', False):
        badges.append('bundle')
        # v2.2.21 — unavailable badge when a component is out of stock and
        # the bundle isn't set to keep selling.
        try:
            b = product.uellow_bundle_id
            if b and b.sudo()._listing_state() == 'badge':
                badges.append('bundle_unavailable')
        except Exception:
            pass
    return badges


def serialize_product_full(product, lang='en_US'):
    """Detail-page shape — includes long description, variants, attributes."""
    card = serialize_product_card(product, lang)
    if not card:
        return None
    # Long description — v2.1.16: PRIMARY source is website_description
    # (the "وصف الصفحة" website tab, full HTML incl. images, per user
    # request) with description_ecommerce as the fallback.
    # `description_sale` (order-line snippet) is still the short description.
    public_desc = {'en': '', 'ar': ''}
    if 'website_description' in product._fields:
        public_desc = bilingual(product, 'website_description')
    if not (public_desc.get('en') or public_desc.get('ar')):
        public_desc = bilingual(product, 'description_ecommerce') \
            if 'description_ecommerce' in product._fields \
            else {'en': '', 'ar': ''}
    desc = bilingual(product, 'description_sale')
    if not (desc.get('en') or desc.get('ar')):
        desc = public_desc

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

    # Gallery — v2.2.26: full-res image_1920 on the product page (the detail
    # gallery was image_1024 and looked soft on big phones / zoom).
    images = [img_url('product.template', product.id, 'image_1920',
                      unique=product.write_date)]
    for img in product.product_template_image_ids[:20]:
        images.append(img_url('product.image', img.id, 'image_1920',
                              unique=img.write_date))
    # v2.2.21 — a bundle (merge mode) aggregates every component's photos +
    # videos so the gallery shows everything inside.
    _bundle_gallery = None
    try:
        if getattr(product, 'is_bundle', False) and product.uellow_bundle_id \
                and product.uellow_bundle_id.gallery_mode == 'merge':
            _bundle_gallery = product.uellow_bundle_id.sudo()._gallery(lang)
            for u in _bundle_gallery.get('images', []):
                if u not in images:
                    images.append(u)
    except Exception:
        _bundle_gallery = None

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
    # v2.2.21 — append the bundle's component videos (merge mode).
    if _bundle_gallery and _bundle_gallery.get('videos'):
        have = {v.get('id') for v in videos}
        for v in _bundle_gallery['videos']:
            if v.get('id') not in have:
                videos.append(v)
    return {
        **card,
        'flash_sale': flash_sale,
        'description_short': desc,
        'description_html': public_desc,
        'ranks': _product_ranks_full(product),
        'price_history': _price_history(product),
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
        'vendor': _vendor_ref(product),
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
        # v2.2.20 — when this product IS a bundle, expose its components +
        # savings so the product page lists everything inside.
        'bundle': _bundle_detail(product, lang),
        # v2.2.26 — Brain BNPL: installments nudge ONLY when the engine is
        # on, the product clears the min price, and (if guard on) the
        # margin absorbs the provider fee. None otherwise.
        'installments': _bnpl_offer(product, lang),
    }


def _bnpl_offer(product, lang='en_US'):
    """Margin-aware installments offer dict, or None. Guarded."""
    try:
        Brain = request.env.get('uellow.brain.config')
        if Brain is None or not Brain.sudo().is_on('bnpl_enabled'):
            return None
        cfg = Brain.sudo().get_config()
        price = float(product.list_price or 0)
        if price < (cfg.bnpl_min_price or 0) or price <= 0:
            return None
        fee = price * (cfg.bnpl_fee_pct or 0) / 100.0 + (cfg.bnpl_fee_fixed or 0)
        if cfg.bnpl_respect_guard and cfg.bnpl_fee_payer == 'merchant':
            if not cfg.margin_ok(product, price, extra_fee=fee):
                return None
        n = max(int(cfg.bnpl_installments or 4), 2)
        per = round(price / n, 3)
        # v2.2.27 — Uellow's installments partner is Taly (Deema soon).
        prov = cfg.bnpl_provider or 'taly'
        prov_label = {'taly': 'Taly', 'deema': 'Deema'}.get(prov, 'Installments')
        return {
            'available': True,
            'provider': prov,
            'provider_label': prov_label,
            'count': n,
            'per_installment': per,
            'label': {
                'en': 'Split in %d interest-free payments of %.3f' % (n, per),
                'ar': 'قسّمها على %d دفعات بدون فوائد، %.3f لكل دفعة' % (n, per),
            },
        }
    except Exception:
        return None


def _bundle_detail(product, lang='en_US'):
    """Full bundle payload for a bundle product's detail page, else None."""
    try:
        if not getattr(product, 'is_bundle', False):
            return None
        b = product.uellow_bundle_id
        if not b:
            return None
        return b.sudo().to_mobile_dict(lang, with_components=True)
    except Exception:
        return None


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
            # v2.0.87 — Bunny Stream: external CDN, HLS playback. The
            # `bunny_playback_url` field is computed from the library's
            # pull zone in res.config.settings.
            if (getattr(v, 'video_type', '') == 'bunny_stream'
                    and getattr(v, 'bunny_playback_url', '')):
                item['file_url'] = v.bunny_playback_url
                item['mime'] = 'application/vnd.apple.mpegurl'
                # Bunny iframe embed — the app's webview player can't play
                # raw HLS in a <video> tag, but Bunny's hosted player can.
                gid = (getattr(v, 'bunny_video_id', '') or '').strip()
                lib = (request.env['ir.config_parameter'].sudo()
                       .get_param('uellow_cdn_video.bunny_library_id') or '').strip()
                if gid and lib:
                    item['embed_url'] = (
                        'https://iframe.mediadelivery.net/embed/%s/%s'
                        '?autoplay=true&preload=true' % (lib, gid))
                # Prefer the auto thumbnail when set and no local one was uploaded
                if (not item['thumbnail']) and getattr(v, 'bunny_thumb_auto', False):
                    item['thumbnail'] = getattr(v, 'bunny_thumb_url', '') or None
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
    website = get_website()
    base = [
        ('is_published', '=', True),
        ('active', '=', True),
        # visible on: truly website-agnostic (NO primary AND NO extras —
        # v2.1.92 fix: an empty primary with extras set used to leak the
        # product onto every site) OR the primary website OR any of the
        # product's extra (multi-website) sites.
        '|', '|',
            '&', ('website_id', '=', False),
                 ('uellow_extra_website_ids', '=', False),
            ('website_id', '=', website.id),
            ('uellow_extra_website_ids', 'in', website.id),
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
            sors = [('name', 'ilike', search),
                    ('description_sale', 'ilike', search)]
            # v2.2.16 — digit-only query also matches ID / exact barcode.
            if search.isdigit():
                sors = [('id', '=', int(search)),
                        ('barcode', '=', search)] + sors
            domain += ['|'] * (len(sors) - 1) + sors

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

        # v2.2.46 — installments-eligible only (price ≥ Taly minimum). Powers
        # the "See all" of the new Installments home block.
        if p.get('installments') in ('1', 'true', True):
            try:
                from odoo.addons.uellow_mobile_pages.models.block_resolver \
                    import _installments_domain
                domain += _installments_domain(request.env)
            except Exception:
                pass

        # v2.0.89 — Free shipping filter. The DB-level filter only covers
        # products explicitly flagged; products inheriting via category /
        # tag get filtered Python-side below.
        free_shipping_flag = p.get('free_shipping') in ('1', 'true', True)
        if free_shipping_flag:
            # Cheap pre-filter: products that ARE directly flagged OR
            # belong to ANY free-shipping category OR carry ANY free-
            # shipping tag. We use Python post-filter to honor parent
            # category traversal that `_is_free_shipping` does.
            Tmpl_check = request.env['product.template']
            cat_dom = []
            if 'free_shipping' in request.env['product.public.category']._fields:
                free_cats = request.env['product.public.category'].sudo().search(
                    [('free_shipping', '=', True)])
                if free_cats:
                    cat_dom = [('public_categ_ids', 'in', free_cats.ids)]
            tag_dom = []
            if ('free_shipping' in request.env['product.tag']._fields
                    and 'product_tag_ids' in Tmpl_check._fields):
                free_tags = request.env['product.tag'].sudo().search(
                    [('free_shipping', '=', True)])
                if free_tags:
                    tag_dom = [('product_tag_ids', 'in', free_tags.ids)]
            or_parts = []
            if 'free_shipping' in Tmpl_check._fields:
                or_parts.append([('free_shipping', '=', True)])
            if cat_dom:
                or_parts.append(cat_dom)
            # v2.2.20 — badge-safe conditional rules contribute too.
            try:
                Rule = request.env.get('uellow.freeship.rule')
                if Rule is not None:
                    for leaf in Rule.sudo().badge_domain_or():
                        or_parts.append([leaf])
            except Exception:
                pass
            if tag_dom:
                or_parts.append(tag_dom)
            if or_parts:
                # Combine all parts with OR
                combined = or_parts[0]
                for part in or_parts[1:]:
                    combined = ['|'] + combined + part
                domain += combined

        # v2.0.80 — minimum rating filter (4 = "4★ & up"). Only applied
        # when the product.template has a `rating_avg` aggregate.
        try:
            mr = float(p.get('min_rating') or 0)
            if mr > 0 and 'rating_avg' in request.env['product.template']._fields:
                domain.append(('rating_avg', '>=', mr))
        except Exception:
            pass

        # v2.1.92 — 'discount' feed (promo "mega" block "All" button):
        # only products on sale, biggest markdown first.
        if p.get('sort') == 'discount':
            domain = domain + [('compare_list_price', '>', 0)]

        # Sort
        sort_map = {
            'newest':       'create_date desc',
            'oldest':       'create_date asc',
            'price_asc':    'list_price asc',
            'price_desc':   'list_price desc',
            'name':         'name asc',
            # v2.1.66 — 'popular' handled below (sales_count is a
            # non-stored compute and cannot be a search order).
            'popular':      'create_date desc',
            'discount':     'compare_list_price desc',
            'top_rated':    'rating_avg desc' if 'rating_avg' in request.env['product.template']._fields else 'create_date desc',
        }
        # v2.2.25 — Uellow Brain: "best_match" sorts by the precomputed,
        # indexed brain_score (cost/margin-driven). Guarded: only when the
        # field exists AND the engine is enabled; else falls back safely.
        req_sort = p.get('sort')
        Brain = request.env.get('uellow.brain.config')
        brain_on = False
        try:
            brain_on = (Brain is not None
                        and 'brain_score' in request.env['product.template']._fields
                        and Brain.sudo().is_on())
        except Exception:
            brain_on = False
        if brain_on:
            sort_map['best_match'] = 'brain_score desc, create_date desc'
            # optional: make best_match the default when configured.
            # v2.2.26 — A/B: when enabled, only a deterministic % of users
            # get Best Match as default; the rest get Newest (to measure).
            if not req_sort:
                try:
                    cfgb = Brain.sudo().get_config()
                    if cfgb.default_sort_best_match:
                        key = None
                        try:
                            pp = current_partner()
                            key = pp.id if pp else (
                                request.httprequest.headers.get('X-Device-Id')
                                or request.httprequest.headers.get('X-Cart-Token'))
                        except Exception:
                            key = None
                        req_sort = ('best_match'
                                    if cfgb.ab_use_best_match(key) else 'newest')
                except Exception:
                    pass
        order = sort_map.get(req_sort or p.get('sort', 'newest'),
                             'create_date desc')

        Tmpl = request.env['product.template'].sudo()
        if p.get('sort') == 'popular':
            all_recs = Tmpl.browse(_top_selling_ids(domain, limit=1000))
        else:
            all_recs = Tmpl.search(domain, order=order)
        # v2.2.25 — Brain Phase 2: personalized re-rank for Best Match.
        # Light: re-orders only the top brain candidates by
        # brain_score × affinity(taste). Members → profile row; guests →
        # X-Taste header (no DB). Fully guarded.
        if brain_on and (req_sort or p.get('sort')) == 'best_match':
            try:
                Taste = request.env.get('uellow.taste.profile')
                prof = {}
                if Taste is not None:
                    cfg2 = Brain.sudo().get_config()
                    mode = cfg2.personalization_mode
                    if mode in ('members', 'opt_in', 'full'):
                        partner = current_partner()
                        if partner:
                            prof = Taste.sudo().get_dict(partner.id)
                    if not prof and mode == 'full':
                        prof = Taste.sudo().parse_header(
                            request.httprequest.headers.get('X-Taste'))
                if prof:
                    cand = all_recs[:300]
                    ranked = sorted(
                        cand,
                        key=lambda r: -((r.brain_score or 0)
                                        * Taste.sudo().affinity(prof, r)))
                    rest = all_recs[300:]
                    all_recs = Tmpl.browse([r.id for r in ranked]) | rest
            except Exception:
                pass
        # v2.2.21 — minimum DISCOUNT % filter (discount_pct is a computed,
        # non-stored value → post-filter in Python). Used by the
        # filtered-link "min discount" control.
        try:
            min_disc = int(p.get('min_discount') or 0)
        except Exception:
            min_disc = 0
        if min_disc > 0:
            def _disc(r):
                cmp = r.compare_list_price or 0
                lp = r.list_price or 0
                return int(round((1 - lp / cmp) * 100)) if cmp > lp > 0 else 0
            all_recs = all_recs.filtered(lambda r: _disc(r) >= min_disc)
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

    # ─── Global filter spec (any non-category product page) ───────────
    @http.route('/api/mobile/v2/products/filters', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def products_filters(self, **kw):
        """v2.2.24 — price range + attribute facets for ANY product feed
        that isn't a single category (newest / discounted / filtered-set
        links…). Optional `category_id` narrows it; otherwise it spans the
        published catalogue (sampled)."""
        p = get_payload()
        domain = _domain_published_for_app()
        cat_id = p.get('category_id')
        if cat_id:
            try:
                domain += [('public_categ_ids', 'child_of', int(cat_id))]
            except Exception:
                pass
        if p.get('on_sale') in ('1', 'true', True):
            domain += [('compare_list_price', '>', 0)]
        Tmpl = request.env['product.template'].sudo()
        recs = Tmpl.search(domain, order='create_date desc', limit=2000)
        prices = [r.list_price for r in recs if r.list_price]
        ICP = request.env['ir.config_parameter'].sudo()
        hidden = {int(t) for t in
                  (ICP.get_param('uellow_mobile.hidden_filter_attrs', '') or '')
                  .split(',') if t.strip().isdigit()}
        Line = request.env['product.template.attribute.line'].sudo()
        lines = Line.search([('product_tmpl_id', 'in', recs.ids)])
        buckets = {}
        for line in lines:
            attr = line.attribute_id
            if attr.id in hidden:
                continue
            is_brand = is_brand_attribute(attr)
            b = buckets.setdefault(attr.id, {
                'id': attr.id, 'name': bilingual(attr, 'name'),
                'display_type': attr.display_type or 'radio',
                'is_brand': is_brand, 'values': {}})
            for v in line.value_ids:
                # v2.2.40 — brand chips show the real brand logo.
                vimg = brand_value_logo(v) if is_brand else (
                    img_url('product.attribute.value', v.id, 'image',
                            unique=v.write_date) if v.image else None)
                vb = b['values'].setdefault(v.id, {
                    'id': v.id, 'name': bilingual(v, 'name'),
                    'html_color': v.html_color or '',
                    'image': vimg,
                    'count': 0})
                vb['count'] += 1
        filters = []
        for b in buckets.values():
            b['values'] = sorted(b['values'].values(), key=lambda x: -x['count'])
            filters.append(b)
        filters.sort(key=lambda b: -sum(v['count'] for v in b['values']))
        return ok({
            'price': {
                'min': round(min(prices), 3) if prices else 0.0,
                'max': round(max(prices), 3) if prices else 0.0,
                'currency': request.env.company.currency_id.symbol or 'KD',
            },
            'attributes': filters[:12],
        })

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

        base_domain = _domain_published_for_app()
        domain = list(base_domain)
        # v2.0.37 — accept narrowing: ?category_id=…&sort=…
        cat_id = p.get('category_id')
        if cat_id:
            try:
                domain = domain + [('public_categ_ids', 'in', [int(cat_id)])]
            except Exception:
                pass
        # v2.2.08 — ?promotion_id= narrowing (explore-more on promotion
        # landing pages keeps the campaign filter through load-more).
        promo_id = p.get('promotion_id')
        if promo_id:
            try:
                Line = request.env.get('mobile.promotion.line')
                tmpl_ids = Line.sudo().search([
                    ('promotion_id', '=', int(promo_id)),
                    ('state', '=', 'approved'),
                ]).mapped('product_tmpl_id').ids if Line is not None else []
                domain = domain + [('id', 'in', tmpl_ids or [0])]
            except Exception:
                domain = domain + [('id', 'in', [0])]
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
                # v2.2.46 — a narrowing filter (category/promotion) can yield
                # zero. NEVER leave "Explore more" empty: fall back to the
                # base published feed so the block always shows products.
                if not all_ids and domain != base_domain:
                    all_ids = Tmpl.search(base_domain).ids
                    _cache_key = _freeze(base_domain)
                # Only cache a NON-empty result — a transient 0 would otherwise
                # stick for 60s and the block would look broken to everyone.
                if all_ids:
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
        # Lightweight view counter (vendor KPIs). Raw SQL = no ORM recompute.
        try:
            request.env.cr.execute(
                "UPDATE product_template SET uellow_view_count = "
                "COALESCE(uellow_view_count, 0) + 1 WHERE id = %s", (product_id,))
        except Exception:
            pass
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

        # v2.1.35 — the live source is rating.rating (the Reviews module):
        # app-submitted reviews land there consumed=False (pending) and
        # appear here only after an admin approves (consumed=True).
        items = []
        meta = {'page': 1, 'per_page': 20, 'total': 0}
        breakdown = {'5': 0, '4': 0, '3': 0, '2': 0, '1': 0}
        avg, total = 0.0, 0
        try:
            Rating = request.env['rating.rating'].sudo()
            recs = Rating.search([
                ('res_model', '=', 'product.template'),
                ('res_id', '=', product.id),
                ('consumed', '=', True),
                ('rating', '>', 0),
            ], order='create_date desc')
            # v2.1.38 — the AUTHOR also sees their own still-pending
            # review (flagged so the app shows an "under review" chip).
            try:
                partner = current_partner()
            except Exception:
                partner = None
            if partner:
                mine = Rating.search([
                    ('res_model', '=', 'product.template'),
                    ('res_id', '=', product.id),
                    ('consumed', '=', False),
                    ('partner_id', '=', partner.id),
                    ('rating', '>', 0),
                ])
                if mine:
                    recs = mine | recs
            ratings = []
            for r in recs:
                if not r.consumed:
                    continue          # pending: shown to author, NOT counted
                rating = int(round(r.rating or 0))
                ratings.append(float(r.rating or 0))
                if 1 <= rating <= 5:
                    breakdown[str(rating)] = breakdown.get(str(rating), 0) + 1
            total = len(ratings)
            avg = round(sum(ratings) / total, 1) if total else 0.0
            items, meta = paginate(
                recs,
                page=p.get('page', 1),
                per_page=p.get('per_page', 20),
                serializer=_serialize_rating_review,
            )
        except Exception:
            pass
        return ok({
            'reviews': items,
            'summary': {
                'avg': avg,
                'total': total,
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
    @http.route('/api/mobile/v2/products/<int:product_id>/why', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def why_recommended(self, product_id, **kw):
        """v2.2.26 — Brain "why you saw this": transparency + privacy.
        Returns bilingual reasons. Empty list when the engine is off."""
        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return fail('NOT_FOUND', 'Product not found', 404)
        Brain = request.env.get('uellow.brain.config')
        reasons = []
        try:
            if Brain is not None and Brain.sudo().is_on():
                cfg = Brain.sudo().get_config()
                prof = {}
                Taste = request.env.get('uellow.taste.profile')
                if Taste is not None and cfg.personalization_mode in (
                        'members', 'opt_in', 'full'):
                    pp = current_partner()
                    if pp:
                        prof = Taste.sudo().get_dict(pp.id)
                    if not prof and cfg.personalization_mode == 'full':
                        prof = Taste.sudo().parse_header(
                            request.httprequest.headers.get('X-Taste'))
                reasons = cfg.why_reasons(product, prof)
        except Exception:
            reasons = []
        return ok({'reasons': reasons})

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
        # v2.1.29 — unbounded related with pagination (the app infinite-
        # loads 3 pages then shows a Load-more button).
        try:
            page = max(1, int(kw.get('page') or 1))
            per_page = min(40, max(1, int(kw.get('per_page') or 12)))
        except Exception:
            page, per_page = 1, 12
        Tmpl = request.env['product.template'].sudo()
        total = Tmpl.search_count(domain)
        items = Tmpl.search(domain, order='create_date desc',
                            limit=per_page, offset=(page - 1) * per_page)
        return ok({
            'items': [serialize_product_card(p, lang) for p in items],
            'page': page, 'per_page': per_page, 'total': total,
            'has_next': page * per_page < total,
        })

    # ─── Top selling ──────────────────────────────────────────────────
    @http.route('/api/mobile/v2/products/top-selling', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def top_selling(self, **kw):
        lang = get_lang()
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app()
        # v2.1.66 — sales_count is non-stored; rank via sale.report.
        items = Tmpl.browse(_top_selling_ids(domain, limit=20))
        return ok([serialize_product_card(p, lang) for p in items])

    # ─── Bestsellers page (v2.1.61) — ranked + paginated ─────────────
    # Backs the «عرض المزيد» of the Champions Arena block: same daily
    # rank ladder the block uses (uellow.product.rank), then fills the
    # tail with sales_count ordering so deeper pages stay meaningful.
    @http.route('/api/mobile/v2/products/bestsellers', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def bestsellers_page(self, **kw):
        p = get_payload()
        try:
            page = max(1, int(p.get('page') or 1))
        except Exception:
            page = 1
        try:
            per = min(40, max(1, int(p.get('per_page') or 20)))
        except Exception:
            per = 20
        lang = get_lang()
        try:
            cat_id = int(p.get('category_id') or 0)
        except Exception:
            cat_id = 0
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app()
        if cat_id:
            domain.append(('public_categ_ids', 'child_of', cat_id))
        ranked = Tmpl.browse([])
        try:
            Rank = request.env.get('uellow.product.rank')
            if Rank is not None:
                ranked = Rank.sudo().top_products(
                    category_id=(cat_id or None), website_id=None, limit=120)
                ranked = ranked.filtered(lambda t: t.is_published)
        except Exception:
            ranked = Tmpl.browse([])
        ids = list(ranked.ids)
        need = page * per + 1
        if len(ids) < need:
            # v2.1.66 — fill the tail by REAL sold qty (sale.report);
            # ordering by the non-stored sales_count crashed page 2+.
            extra = _top_selling_ids(
                domain + [('id', 'not in', ids)], limit=need - len(ids))
            ids += extra
        sl = ids[(page - 1) * per: page * per]
        items = []
        for n, t in enumerate(Tmpl.browse(sl)):
            d = serialize_product_card(t, lang)
            # 'rank' is already the badge map on the card → own key.
            d['bs_rank'] = (page - 1) * per + n + 1
            items.append(d)
        return ok({'items': items, 'page': page,
                   'has_more': len(ids) > page * per})

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

def _serialize_rating_review(r):
    """v2.1.35 — rating.rating record → the app's review JSON shape."""
    photos = []
    for img in getattr(r, 'review_image_ids', []):
        if img.image:
            photos.append(img_url('rating.review.image', img.id, 'image',
                                  unique=img.write_date))
    return {
        'id':     r.id,
        'rating': int(round(r.rating or 0)),
        'title':  getattr(r, 'review_title', '') or '',
        'body':   r.feedback or '',
        'author': r.partner_id.name if r.partner_id else 'Anonymous',
        'avatar': img_url('res.partner', r.partner_id.id, 'image_128',
                          unique=r.partner_id.write_date)
                  if r.partner_id else None,
        'date':   r.create_date.isoformat() if r.create_date else None,
        'verified_purchase': bool(getattr(r, 'is_verified_purchase', False)),
        'helpful_count': int(getattr(r, 'helpful_count', 0) or 0),
        'photos': photos,
        'pending': not r.consumed,
        'video_url': '',
        'vendor_reply': '',
    }


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


def _price_history(product):
    """Sparkline payload for the product page (90 days)."""
    try:
        Hist = request.env.get('uellow.price.history')
        if Hist is None:
            return None
        return Hist.sudo().history_for(product.id)
    except Exception:
        return None


def _product_ranks_full(product):
    """All categories the product ranks in (product-page strip)."""
    try:
        Rank = request.env.get('uellow.product.rank')
        if Rank is None:
            return []
        cfg = request.env['uellow.rank.config'].sudo().get_config()
        if not cfg.enabled:
            return []
        return [_rank_dict(r) for r in
                Rank.sudo().all_for(product.id,
                                    website_id=get_website().id)[:3]]
    except Exception:
        return []


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
        website = get_website()
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
