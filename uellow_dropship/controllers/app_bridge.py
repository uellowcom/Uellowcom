# -*- coding: utf-8 -*-
"""App bridge — make the Uellow World website (id = uellow_dropship.website_id)
serve its ISOLATED dropship catalog through the STANDARD mobile-app API, so the
installed app renders World exactly like any other country/website with NO app
release: same Home / Categories / Product screens, scoped to the World catalog.

How it works
------------
* PRODUCTS: dropship products are materialized into real product.template rows
  flagged is_dropship=True with website_id = World. The standard listing/feed/
  search/detail endpoints scope by website, but website-agnostic products
  (website_id=False) show on EVERY site including World — so we patch the shared
  `_domain_published_for_app` to add `is_dropship=True` on World (and
  `is_dropship=False` everywhere else), mirroring the web `sale_product_domain`
  override. Tapping a card opens the real materialized product unchanged.
* CATEGORIES: the World taxonomy is a SEPARATE model (dropship.category) that
  deliberately never pollutes the shared product.public.category tree. So the
  app's category endpoints are overridden here: on World they serve
  dropship.category (and dropship-scoped product lists); on every other website
  they fall through to super() unchanged.

Everything is gated by `_is_world()` → identical behaviour off-World.
"""
import random
import re

from odoo import http
from odoo.http import request

from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
    get_payload, ok, fail, get_lang, get_website, current_partner,
    bilingual, img_url,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.products import (
    serialize_product_card, _domain_published_for_app, MobileProductsAPI,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.categories import (
    MobileCategoriesAPI,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.orders import (
    MobileOrdersAPI,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.videos import (
    MobileVideosAPI,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.shop_config import (
    MobileShopConfigAPI,
)
from odoo.addons.uellow_mobile_manager.controllers.api_v2.search import (
    MobileSearchAPI,
)
from odoo.addons.uellow_mobile_pages.controllers.pages_public import PagesPublic


# ── World detection ────────────────────────────────────────────────────────
def _world_id():
    try:
        return int(request.env['ir.config_parameter'].sudo()
                   .get_param('uellow_dropship.website_id') or 0)
    except Exception:  # noqa: BLE001
        return 0


def _enabled():
    return request.env['ir.config_parameter'].sudo() \
        .get_param('uellow_dropship.enabled') in ('True', '1', 'true')


def _is_world():
    wid = _world_id()
    if not wid or not _enabled():
        return False
    try:
        return get_website().id == wid
    except Exception:  # noqa: BLE001
        return False


def _ar_code():
    lang = request.env['res.lang'].sudo().search(
        [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
    return lang.code if lang else 'ar_001'


def _world_ship_country():
    """The customer's shipping country for World listing filtering — only when
    the admin enabled `filter_by_ship_country`. Sources: X-Country header (app),
    ?country=, Cloudflare CF-IPCountry. Empty → no filter (show everything)."""
    ICP = request.env['ir.config_parameter'].sudo()
    if ICP.get_param('uellow_dropship.filter_by_ship_country') not in ('True', '1', 'true'):
        return ''
    try:
        h = request.httprequest.headers
        cc = (h.get('X-Country') or h.get('X-Uellow-Country')
              or request.httprequest.args.get('country')
              or h.get('CF-IPCountry') or '').upper().strip()
        return '' if cc in ('', 'XX', 'T1') else cc
    except Exception:  # noqa: BLE001
        return ''


# ── dropship.category → standard serialize_category shape ───────────────────
def _ds_counts():
    """Product count per dropship category code (whole catalog)."""
    DP = request.env['dropship.product'].sudo()
    groups = DP.read_group([('category_name', '!=', False)],
                           ['category_name'], ['category_name'])
    return {g['category_name']: (g.get('category_name_count')
                                 or g.get('__count') or 0)
            for g in groups if g.get('category_name')}


def _ds_cat_dict(dc, counts, ar_code, with_children=False):
    children = []
    if with_children:
        children = [_ds_cat_dict(c, counts, ar_code, with_children=False)
                    for c in dc.child_ids.sorted('sequence')
                    if _node_count(c, counts) > 0]
    cnt = counts.get(dc.code, 0) + sum(ch['product_count'] for ch in children)
    return {
        'id': dc.id,
        'name': {
            'en': dc.with_context(lang='en_US').name or dc.code,
            'ar': (dc.with_context(lang=ar_code).name
                   or dc.with_context(lang='en_US').name or dc.code),
        },
        'parent_id': dc.parent_id.id if dc.parent_id else None,
        'image': _ds_cat_image_url(dc),   # representative product photo tile
        'icon': dc.icon or '🏷️',          # app may use as emoji fallback
        'product_count': cnt,
        'children': children,
    }


def _node_count(dc, counts):
    """Recursive product count for a dropship category (self + descendants)."""
    total = counts.get(dc.code, 0)
    for c in dc.child_ids:
        total += _node_count(c, counts)
    return total


def _ds_cat_image_url(dc):
    """A tile image for a dropship category — the EXACT AliExpress product
    photo, matching what the customer sees on AliExpress itself.

    Priority:
      1. admin-uploaded custom image on the category (manual override),
      2. the real AliExpress CDN photo of the best-rated product in the
         category (no publishing/materialisation needed — every category with
         products gets a genuine image, so the emoji/yellow fallback disappears),
      3. a published World template image (legacy fallback).
    Returns None only when the category is genuinely empty."""
    try:
        # 1. admin-uploaded custom image (highest priority)
        if getattr(dc, 'image', False):
            return '%s/web/image/dropship.category/%d/image?unique=%s' % (
                _world_base_url(), dc.id,
                dc.write_date and dc.write_date.strftime('%s') or '')
        codes = _codes_for(dc)
        if not codes:
            return None
        # 2. real AliExpress product photo (the actual image from AliExpress) —
        #    best-rated in-category product that carries a picture. This is the
        #    provider CDN url the storefront/app already render for feed cards.
        DP = request.env['dropship.product'].sudo()
        rec = DP.search([
            ('category_name', 'in', codes),
            ('image_url', '!=', False),
        ], order='rating desc, id desc', limit=1)
        if rec and rec.image_url:
            return rec.image_url
        # 3. legacy: a published World template image
        Tmpl = request.env['product.template'].sudo()
        t = Tmpl.search([
            ('is_dropship', '=', True),
            ('is_published', '=', True),
            ('image_1920', '!=', False),
            ('dropship_product_id.category_name', 'in', codes),
        ], order='create_date desc', limit=1)
        if not t:
            return None
        return '%s/web/image/product.template/%d/image_512' % (
            _world_base_url(), t.id)
    except Exception:  # noqa: BLE001
        return None


def _codes_for(dc):
    """The dropship category code + all descendant codes (leaf match keys)."""
    codes = [dc.code] if dc.code else []
    for c in dc.child_ids:
        codes += _codes_for(c)
    return codes


def _world_category_products(category_id, p, lang):
    """Serve products of a dropship category as standard product cards."""
    dc = request.env['dropship.category'].sudo().browse(int(category_id))
    if not dc.exists():
        return fail('NOT_FOUND', 'Category not found', 404)
    codes = _codes_for(dc)
    # dropship.category.code == dropship.product.category_name (the readable
    # match key); `category` on the product is the raw provider code — NOT it.
    domain = _domain_published_for_app() + [
        ('dropship_product_id.category_name', 'in', codes)]
    sort_map = {
        'newest': 'create_date desc',
        'price_asc': 'list_price asc',
        'price_desc': 'list_price desc',
        'name': 'name asc',
    }
    order = sort_map.get(p.get('sort') or 'newest', 'create_date desc')
    Tmpl = request.env['product.template'].sudo()
    try:
        _page = max(1, int(p.get('page', 1)))
    except Exception:  # noqa: BLE001
        _page = 1
    try:
        _per = min(100, max(1, int(p.get('per_page', 20))))
    except Exception:  # noqa: BLE001
        _per = 20
    _total = Tmpl.search_count(domain)
    recs = Tmpl.search(domain, order=order, limit=_per,
                       offset=(_page - 1) * _per)
    items = [serialize_product_card(r, lang) for r in recs]
    meta = {'page': _page, 'per_page': _per, 'total': _total,
            'pages': (_total + _per - 1) // _per,
            'has_next': _page * _per < _total}
    return ok(items, meta)


# ── overrides: categories (World serves dropship.category) ──────────────────
class WorldCategoriesAPI(MobileCategoriesAPI):

    def list_categories(self, **kw):
        if not _is_world():
            return super().list_categories(**kw)
        p = get_payload()
        ar_code = _ar_code()
        counts = _ds_counts()
        DC = request.env['dropship.category'].sudo()
        with_children = str(p.get('with_children', 'false')).lower() \
            in ('1', 'true', 'yes')
        if p.get('parent_id'):
            try:
                domain = [('parent_id', '=', int(p['parent_id']))]
            except Exception:  # noqa: BLE001
                domain = [('parent_id', '=', False)]
        else:
            domain = [('parent_id', '=', False)]
        cats = DC.search(domain, order='sequence asc, name asc')
        out = [_ds_cat_dict(c, counts, ar_code, with_children=with_children)
               for c in cats if _node_count(c, counts) > 0]
        return ok(out)

    def category_tree(self, **kw):
        if not _is_world():
            return super().category_tree(**kw)
        ar_code = _ar_code()
        counts = _ds_counts()
        roots = request.env['dropship.category'].sudo().search(
            [('parent_id', '=', False)], order='sequence asc, name asc')
        out = [_ds_cat_dict(c, counts, ar_code, with_children=True)
               for c in roots if _node_count(c, counts) > 0]
        return ok(out)

    def category_detail(self, category_id, **kw):
        if not _is_world():
            return super().category_detail(category_id, **kw)
        dc = request.env['dropship.category'].sudo().browse(int(category_id))
        if not dc.exists():
            return fail('NOT_FOUND', 'Category not found', 404)
        counts = _ds_counts()
        return ok({'category': _ds_cat_dict(dc, counts, _ar_code(),
                                            with_children=True)})

    def category_products(self, category_id, **kw):
        if not _is_world():
            return super().category_products(category_id, **kw)
        return _world_category_products(category_id, get_payload(), get_lang())

    def category_filters(self, category_id, **kw):
        """World filter spec: price range + attribute facets built from the
        DROPSHIP products in this dropship.category. The base endpoint browses
        product.public.category and 404s on a dropship-category id → the app's
        filter dialog came back empty ('doesn't work')."""
        if not _is_world():
            return super().category_filters(category_id, **kw)
        dc = request.env['dropship.category'].sudo().browse(int(category_id))
        if not dc.exists():
            return fail('NOT_FOUND', 'Category not found', 404)
        codes = _codes_for(dc)
        domain = _domain_published_for_app() + [
            ('dropship_product_id.category_name', 'in', codes)]
        Tmpl = request.env['product.template'].sudo()
        recs = Tmpl.search(domain, limit=2000)
        prices = [r.list_price for r in recs if r.list_price]
        min_p = min(prices) if prices else 0.0
        max_p = max(prices) if prices else 0.0

        ICP = request.env['ir.config_parameter'].sudo()
        hidden = {int(t) for t in (ICP.get_param(
            'uellow_mobile.hidden_filter_attrs', '') or '').split(',')
            if t.strip().isdigit()}
        Line = request.env['product.template.attribute.line'].sudo()
        lines = Line.search([('product_tmpl_id', 'in', recs.ids)])
        buckets = {}
        for line in lines:
            attr = line.attribute_id
            if attr.id in hidden:
                continue
            b = buckets.setdefault(attr.id, {
                'id': attr.id, 'name': bilingual(attr, 'name'),
                'display_type': attr.display_type or 'radio',
                'is_brand': False, 'values': {}})
            for v in line.value_ids:
                vb = b['values'].setdefault(v.id, {
                    'id': v.id, 'name': bilingual(v, 'name'),
                    'html_color': v.html_color or '',
                    'image': (img_url('product.attribute.value', v.id, 'image',
                                      unique=v.write_date) if v.image else None),
                    'count': 0})
                vb['count'] += 1
        filters = []
        for b in buckets.values():
            b['values'] = sorted(b['values'].values(), key=lambda x: -x['count'])
            filters.append(b)
        filters.sort(key=lambda b: -sum(v['count'] for v in b['values']))
        cur = (get_website().company_id.currency_id.symbol
               if get_website() and get_website().company_id else None)
        return ok({
            'price': {'min': round(min_p, 3), 'max': round(max_p, 3),
                      'currency': cur or '$'},
            'attributes': filters,
        })


# ── override: list_products (World + category_id → dropship category) ────────
class WorldProductsAPI(MobileProductsAPI):

    def list_products(self, **kw):
        if _is_world():
            p = get_payload()
            if p.get('category_id'):
                return _world_category_products(
                    p['category_id'], p, get_lang())
        return super().list_products(**kw)

    def reviews(self, product_id, **kw):
        # On World, dropship products have no on-site rating.rating reviews —
        # serve the cached AliExpress reviews (with buyer photos) in the app's
        # native reviews shape so the existing reviews UI renders them.
        if _is_world():
            try:
                product = request.env['product.template'].sudo().browse(int(product_id))
                if product.exists() and product.is_dropship and product.dropship_product_id:
                    p = get_payload()
                    built = _world_reviews_payload(
                        product.dropship_product_id.sudo(),
                        page=p.get('page', 1), per_page=p.get('per_page', 20))
                    if built:
                        items, summary, meta = built
                        return ok({'reviews': items, 'summary': summary}, meta)
            except Exception:  # noqa: BLE001 - never break the reviews endpoint
                pass
        return super().reviews(product_id, **kw)


# ── override: product-page delivery block (China shipping, not local carriers) ─
# The app's native delivery card fetches /orders/delivery-eta, which returns the
# LOCAL carriers (Bosta/etc. — wrong for a China-shipped World product). On World
# we replace it with a single "Ships from China · N–M days · Free" line in the
# exact {lines:[{name,status,text,price,free_over,cutoff}]} shape the card renders.
class WorldOrdersAPI(MobileOrdersAPI):

    def delivery_eta(self, **kw):
        if _is_world():
            try:
                icp = request.env['ir.config_parameter'].sudo()
                dmin = int(icp.get_param(
                    'uellow_dropship.world_ship_days_min', 10) or 10)
                dmax = int(icp.get_param(
                    'uellow_dropship.world_ship_days_max', 14) or 14)
                lines = [{
                    'cutoff': '',
                    'price': 0.0,
                    'free_over': 0.0,
                    'name': {'en': 'International Shipping',
                             'ar': 'الشحن الدولي'},
                    'status': 'now',
                    'text': {
                        'en': '\U0001F69A Ships from China · %d–%d days · '
                              'Free' % (dmin, dmax),
                        'ar': '\U0001F69A يُشحن من الصين · %d–%d يوم · '
                              'مجاني' % (dmin, dmax),
                    },
                }]
                country = (kw.get('country')
                           or request.httprequest.headers.get('CF-IPCountry')
                           or '').upper().strip()
                return ok({'country': country, 'lines': lines})
            except Exception:  # noqa: BLE001 - never break the delivery block
                pass
        return super().delivery_eta(**kw)


# ── override: dynamic home page (World gets its own home, others unchanged) ──
# mobile.page.slug is globally unique, so we can't have a second page slug='home'.
# Instead the World home lives under slug 'world_home' (targeted at website 19)
# and we remap the app's home request to it only on World.
class WorldPagesAPI(PagesPublic):

    def get_page(self, slug, **kw):
        if slug == 'home' and _is_world():
            return super().get_page('world_home', **kw)
        return super().get_page(slug, **kw)


# AliExpress serves the templated player URL
# (…/play/u/ae_sg_item/<seller>/…/t/10301/<id>.mp4) as a low-res SD stream — the
# cause of the "blurry Reels" complaint. The canonical …/play/<id>.mp4 form
# redirects to the HD master when the seller uploaded one (~half the catalog) and
# to the same SD otherwise — so this rewrite is a pure upgrade, never worse.
_VID_TMPL_RE = re.compile(
    r'^(https?://video\.aliexpress-media\.com)/play/u/.*/(\d+)\.mp4', re.I)


def _hd_video_url(url):
    if not url:
        return url
    m = _VID_TMPL_RE.match(url)
    if m:
        return '%s/play/%s.mp4' % (m.group(1), m.group(2))
    return url


# ── override: Reels feed (World videos come from the provider mp4, not the ────
# on-site product.video system). Dropship products carry the AliExpress product
# video in `dropship_product_id.video_url` (a raw mp4), which was deliberately
# NOT materialized into product.video (Odoo's product.video only speaks
# YouTube/Vimeo/Bunny embeds). So on World the standard Reels feed — which needs
# `has_product_video=True` — is always empty. Here we build the feed directly
# from the provider video_url in the exact item shape the Reels UI renders.
def _world_video_item(p, lang, partner):
    """Reels slide for a World product, sourced from the provider mp4. None if
    the product has no video."""
    ds = p.dropship_product_id
    url = _hd_video_url(ds.video_url if ds else None)
    if not url:
        return None
    card = serialize_product_card(p, lang)
    if not card:
        return None
    vid = {
        'id': 0,
        'title': p.with_context(lang=lang).name or '',
        'type': 'file',
        'embed_url': '',
        'tiktok_url': '',
        'tiktok_video_id': '',
        'video_url': url,
        'file_url': url,           # raw provider mp4 — the on-device player
        'mime': 'video/mp4',       # streams it directly (no server proxy)
        'thumbnail': card.get('image') or card.get('image_url'),
    }
    try:
        views = int(getattr(ds, 'orders_count', 0) or 0) \
            or int(getattr(ds, 'review_count', 0) or 0)
    except Exception:  # noqa: BLE001
        views = 0
    return {
        'product': card,
        'video': vid,
        'video_count': 1,
        'stats': {'views': views, 'shares': 0,
                  'comments': 0, 'wishlist': 0},
        'is_wishlisted': _world_is_wishlisted(partner, p),
    }


def _world_is_wishlisted(partner, tmpl):
    if not partner or not tmpl:
        return False
    try:
        Wish = request.env.get('mobile.wishlist')
        vids = tmpl.product_variant_ids.ids
        if Wish is None or not vids:
            return False
        return bool(Wish.sudo().search_count(
            [('partner_id', '=', partner.id), ('product_id', 'in', vids)]))
    except Exception:  # noqa: BLE001
        return False


class WorldVideosAPI(MobileVideosAPI):

    def videos_feed(self, **kw):
        if not _is_world():
            return super().videos_feed(**kw)
        lang = get_lang()
        partner = current_partner()
        try:
            cursor = int(kw.get('cursor') or 0)
        except Exception:  # noqa: BLE001
            cursor = 0
        try:
            limit = max(1, min(30, int(kw.get('limit') or 10)))
        except Exception:  # noqa: BLE001
            limit = 10
        Tmpl = request.env['product.template'].sudo()
        # _domain_published_for_app is World-patched → already is_dropship-only.
        base = _domain_published_for_app(include_oos=True)
        base.append(('dropship_product_id.video_url', '!=', False))
        seed = kw.get('seed')
        try:
            seed = int(seed) if seed not in (None, '') else None
        except Exception:  # noqa: BLE001
            seed = None
        if seed is not None:
            all_ids = Tmpl.search(base).ids
            random.Random(seed).shuffle(all_ids)
            offset = cursor if cursor > 0 else 0
            window = all_ids[offset:offset + limit * 4]
            items, consumed = [], 0
            for p in Tmpl.browse(window):
                consumed += 1
                it = _world_video_item(p, lang, partner)
                if it:
                    items.append(it)
                if len(items) >= limit:
                    break
            new_off = offset + consumed
            return ok({'items': items, 'cursor': new_off,
                       'has_more': new_off < len(all_ids)})
        domain = list(base)
        if cursor > 0:
            domain.append(('id', '<', cursor))
        candidates = Tmpl.search(domain, order='write_date desc',
                                 limit=limit * 4)
        items, last_id = [], cursor
        for p in candidates:
            it = _world_video_item(p, lang, partner)
            if it:
                items.append(it)
                last_id = p.id
            if len(items) >= limit:
                break
        return ok({'items': items, 'cursor': last_id,
                   'has_more': len(items) >= limit})

    def videos_search(self, **kw):
        if not _is_world():
            return super().videos_search(**kw)
        lang = get_lang()
        partner = current_partner()
        q = (kw.get('q') or '').strip()
        try:
            limit = max(1, min(60, int(kw.get('limit') or 40)))
        except Exception:  # noqa: BLE001
            limit = 40
        if not q:
            return ok({'items': []})
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app(include_oos=True)
        domain.append(('dropship_product_id.video_url', '!=', False))
        domain += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        items = []
        for p in Tmpl.search(domain, limit=limit * 3):
            it = _world_video_item(p, lang, partner)
            if it:
                items.append(it)
            if len(items) >= limit:
                break
        return ok({'items': items, 'query': q})


# ── override: brands + shop config (World dropship catalog has no brands) ─────
# The brands row/screen counts brand attribute values against a plain
# is_published domain (no website/dropship scope), so on World it would show the
# MAIN-STORE (Kuwait) brands. World's materialized products carry no brand
# attribute at all, so the correct World result is "no brands": we hide the row
# (show_brands=False) and return an empty brands list + empty For-You (which
# otherwise inherits the main store's hand-picked Kuwait categories/brands).
class WorldShopConfigAPI(MobileShopConfigAPI):

    def brands(self, **kw):
        if _is_world():
            return ok({'brands': []})
        return super().brands(**kw)

    def shop_config(self, **kw):
        if not _is_world():
            return super().shop_config(**kw)
        return ok({
            'show_recent': True,
            'show_products': True,
            'show_brands': False,
            'foryou_enabled': False,
            'foryou': {'categories': [], 'brands': []},
        })


# ── domain patch: isolate is_dropship on/off World across ALL app endpoints ──
# The standard `_domain_published_for_app` lets website-agnostic products
# (website_id=False) show on every site — including World. Mirror the web
# `sale_product_domain` override: World → only is_dropship products; every other
# site → never dropship. Patch each api_v2 module that imported the helper (they
# each hold their own module-level reference from `from .products import ...`).
import importlib  # noqa: E402


def _install_domain_patch():
    from odoo.addons.uellow_mobile_manager.controllers.api_v2 import (
        products as _pmod,
    )
    orig = _pmod._domain_published_for_app
    if getattr(orig, '_world_patched', False):
        return

    def _patched(include_oos=False):
        dom = list(orig(include_oos=include_oos))
        try:
            world = _is_world()
        except Exception:  # noqa: BLE001
            world = False
        dom.append(('is_dropship', '=', True) if world
                   else ('is_dropship', '=', False))
        return dom

    _patched._world_patched = True
    for _name in ('products', 'categories', 'search', 'vendors', 'videos'):
        try:
            m = importlib.import_module(
                'odoo.addons.uellow_mobile_manager.controllers.api_v2.'
                + _name)
            if hasattr(m, '_domain_published_for_app'):
                m._domain_published_for_app = _patched
        except Exception:  # noqa: BLE001
            pass


_install_domain_patch()


# ── geo-IP display currency for World (default USD, switches by visitor) ─────
# The World store is a global dropship catalog priced in the company currency
# (KWD) and materialized once. Its DISPLAY currency defaults to USD but follows
# the VISITOR's physical location: a Kuwaiti sees KWD, a Saudi SAR, an unmapped
# country falls back to USD. We deliberately do NOT use the app's *selected*
# country here — on World that is the carrier country (China), not where the
# shopper actually is. Every price already flows through `_common.fmt_price`,
# which calls the module-global `web_currency`; patching that ONE symbol re-
# prices cards, detail, cart, shipping and loyalty in a single place. Off-World
# the original per-website mapping is untouched.
_GEO_SKIP = {'', 'XX', 'T1', 'T'}


def _geo_country_code():
    """Physical visitor ISO country code: Cloudflare header first (accurate in
    prod), then Odoo GeoIP on the client IP. '' when unknown."""
    try:
        cc = (request.httprequest.headers.get('CF-IPCountry')
              or '').upper().strip()
        if cc and cc not in _GEO_SKIP:
            return cc
    except Exception:  # noqa: BLE001
        pass
    try:
        ip = request.httprequest.remote_addr
        cc = request.env['res.country'].sudo()._get_country_from_ip(ip)
        if hasattr(cc, 'code'):
            cc = cc.code
        cc = (cc or '').upper().strip()
        if cc and cc not in _GEO_SKIP:
            return cc
    except Exception:  # noqa: BLE001
        pass
    return ''


def _usd():
    return request.env['res.currency'].sudo().with_context(
        active_test=False).search([('name', '=', 'USD')], limit=1)


def _has_rate(cur):
    """Only currencies with an explicit rate row are safe to display — without
    one Odoo silently assumes 1:1 and would mis-price (e.g. show a EUR shopper a
    KWD number as if it were euros)."""
    if not cur:
        return False
    return bool(request.env['res.currency.rate'].sudo()
                .search_count([('currency_id', '=', cur.id)]))


def _world_currency():
    """Display currency for a World visitor: a currency the shopper EXPLICITLY
    picked in the app settings (X-Currency) wins; else their own country's
    currency when we can safely convert to it, else USD."""
    # user-selected currency (app Settings ▸ Currency) takes precedence
    try:
        chosen = (request.httprequest.headers.get('X-Currency')
                  or request.httprequest.args.get('currency') or '').upper().strip()
        if chosen:
            c = request.env['res.currency'].sudo().with_context(
                active_test=False).search([('name', '=', chosen)], limit=1)
            if c and _has_rate(c):
                return c
    except Exception:  # noqa: BLE001
        pass
    usd = _usd()
    cc = _geo_country_code()
    if cc:
        country = request.env['res.country'].sudo().search(
            [('code', '=', cc)], limit=1)
        cur = country.currency_id
        if (cur and cur.active and (not usd or cur.id != usd.id)
                and _has_rate(cur)):
            return cur
    return usd or request.env.company.currency_id


def _world_ship_price(cost, src_code):
    """Convert a provider shipping fee (in src_code, e.g. USD) into the shopper's
    display currency and return a {amount, currency, symbol, digits} money dict."""
    from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
        fmt_price, web_currency,
    )
    Cur = request.env['res.currency'].sudo().with_context(active_test=False)
    src = Cur.search([('name', '=', src_code or 'USD')], limit=1) or web_currency()
    try:
        return fmt_price(cost or 0.0, src)
    except Exception:  # noqa: BLE001
        dst = web_currency()
        return {'amount': round(cost or 0.0, 2), 'currency': dst.name,
                'symbol': dst.symbol or dst.name, 'digits': dst.decimal_places}


def _install_currency_patch():
    from odoo.addons.uellow_mobile_manager.controllers.api_v2 import (
        _common as _cmod,
    )
    orig = _cmod.web_currency
    if getattr(orig, '_world_patched', False):
        return

    def _patched():
        try:
            if _is_world():
                return _world_currency()
        except Exception:  # noqa: BLE001
            pass
        return orig()

    _patched._world_patched = True
    _cmod.web_currency = _patched


_install_currency_patch()


# ── block-resolver patch: World home blocks show the DROPSHIP catalog ────────
# The app page-builder resolver (uellow_mobile_pages.block_resolver) is only
# website-aware through `_site_dom`, which filters by website_id/extras but NOT
# by is_dropship. Website-agnostic main-store products (website_id=False) there-
# fore LEAK into World home blocks, and `resolve_categories` pulls
# `product.public.category` (the main store) instead of World's
# `dropship.category`. We mirror the api_v2 domain patch here so that ON WORLD
# every product block resolves ONLY is_dropship products and cats-grid uses the
# dropship category tree. OFF-WORLD nothing changes (least-risk: we only ADD a
# clause on World; main-store home behaviour is byte-for-byte identical).
def _install_block_resolver_patch():
    from odoo.addons.uellow_mobile_pages.models import block_resolver as _br
    if getattr(_br._site_dom, '_world_patched', False):
        return
    _orig_site_dom = _br._site_dom
    _orig_site_visible = _br._site_visible
    _orig_cats = _br.resolve_categories

    def _site_dom(env):
        dom = list(_orig_site_dom(env))
        try:
            if _is_world():
                dom.append(('is_dropship', '=', True))
        except Exception:  # noqa: BLE001
            pass
        return dom
    _site_dom._world_patched = True

    def _site_visible(env, p):
        if not _orig_site_visible(env, p):
            return False
        try:
            if _is_world():
                return bool(getattr(p, 'is_dropship', False))
        except Exception:  # noqa: BLE001
            pass
        return True

    def _resolve_categories(env, props, lang, block=None):
        try:
            world = _is_world()
        except Exception:  # noqa: BLE001
            world = False
        if not world:
            return _orig_cats(env, props, lang, block=block)
        # World: top-level dropship categories that actually hold products —
        # same output shape as the standard resolver ({items:[{id,name,slug,
        # icon_url,icon}]}) but ids are dropship.category ids so a tap routes
        # through WorldProductsAPI.list_products → _world_category_products.
        try:
            counts = _ds_counts()
            limit = int(props.get('limit') or 12)
            lc = _ar_code() if (lang or '').startswith('ar') else 'en_US'
            DC = env['dropship.category'].sudo()
            roots = DC.search([('parent_id', '=', False)],
                              order='sequence asc, name asc')
            out = []
            for c in roots:
                if _node_count(c, counts) <= 0:
                    continue
                out.append({
                    'id': c.id,
                    'name': (c.with_context(lang=lc).name or c.name
                             or c.code or ''),
                    'slug': '',
                    'icon_url': _ds_cat_image_url(c) or '',
                    'icon': c.icon or '🏷️',
                })
                if len(out) >= limit:
                    break
            return {'items': out}
        except Exception:  # noqa: BLE001
            return _orig_cats(env, props, lang, block=block)

    _br._site_dom = _site_dom
    _br._site_visible = _site_visible
    _br.resolve_categories = _resolve_categories
    for _k in ('cats-grid', 'cats-strip'):
        if _k in _br.RESOLVERS:
            _br.RESOLVERS[_k] = _resolve_categories


_install_block_resolver_patch()


# ── enrich the APP product-detail for World (dropship) products ──────────────
# The standard mobile detail (serialize_product_full) is bare for World items:
# it reads the translated `website_description` (dropship writes the PLAIN
# website_description_en/_ar, so the app got only a ~75-char stub), hardcodes
# "Standard delivery 1-3 days" (wrong — dropship ships from China ~10-14 days),
# and carries no specs/reviews. We patch serialize_product_full to, for dropship
# products only: (1) fill the REAL bilingual description (proxied + absolutized
# so app-embedded images resolve), (2) set the real shipping ETA, (3) add
# structured `specifications` + `review_summary` keys (for a future native app
# UI), and (4) inline a review line + specs table into description_html so the
# CURRENT app renders everything with no release. Website product page is
# untouched (it uses its own dedicated cards). Off-World products fall through.
def _world_base_url():
    """Absolute base URL of the World site so app-embedded HTML resolves media."""
    try:
        site = request.env['website'].sudo().browse(_world_id())
        dom = (site.domain or '').strip().rstrip('/')
        if dom:
            return dom if dom.startswith('http') else ('https://' + dom)
    except Exception:  # noqa: BLE001
        pass
    return 'https://world.uellow.com'


def _absolutize(html, base):
    """Point relative /dropship and /web media at the World host (for the app).

    NB: description_html is a markupsafe.Markup whose .replace() HTML-escapes its
    arguments (so `src="` never matches) — coerce to plain str first.
    """
    if not html:
        return html
    html = str(html)
    return (html.replace('src="/dropship/', 'src="%s/dropship/' % base)
                .replace('src="/web/', 'src="%s/web/' % base))


def _specs_table_html(specs, lang_ar):
    from odoo.tools import html_escape as _e
    if not specs:
        return ''
    head = 'المواصفات' if lang_ar else 'Specifications'
    rows = ''.join(
        '<tr><td style="color:#777;padding:6px 10px;border-bottom:1px solid #eee">'
        '%s</td><td style="padding:6px 10px;border-bottom:1px solid #eee;'
        'font-weight:600">%s</td></tr>' % (_e(s['name']), _e(s['value']))
        for s in specs)
    return ('<h4 style="margin:16px 0 8px">\U0001F4CB %s</h4>'
            '<table style="width:100%%;border-collapse:collapse">%s</table>'
            % (head, rows))


def _review_line_html(rev, lang_ar):
    if not rev:
        return ''
    stars = '★' * rev['stars_full'] + ('☆' if rev['stars_half'] else '')
    parts = ['<span style="color:#F5C320">%s</span> <b>%s</b>'
             % (stars, rev['rating'])]
    if rev.get('review_count'):
        parts.append(('%s مراجعة' if lang_ar else '%s reviews') % rev['review_count'])
    if rev.get('orders_text'):
        parts.append(('\U0001F525 %s تم بيعها' if lang_ar
                      else '\U0001F525 %s sold') % rev['orders_text'])
    return ('<div style="margin:0 0 12px;font-size:15px">%s</div>'
            % ' · '.join(parts))


def _reviews_block_html(reviews, lang_ar):
    """Inline individual customer reviews (text + photo thumbnails) as HTML so
    the CURRENT app — which renders description_html but has no native reviews UI
    yet — still shows real reviews with buyer photos. Photo URLs are already
    absolutized (World host) by the caller."""
    if not reviews:
        return ''
    from odoo.tools import html_escape as _e
    head = 'آراء العملاء' if lang_ar else 'Customer Reviews'
    cards = []
    for r in reviews[:6]:
        stars = '★' * (r.get('stars_full') or 5) + '☆' * (r.get('stars_empty') or 0)
        meta = _e(r.get('name') or 'Shopper')
        if r.get('country'):
            meta += ' · ' + _e(r['country'])
        if r.get('date'):
            meta += ' · ' + _e(r['date'])
        imgs = ''
        for u in (r.get('images') or [])[:4]:
            imgs += ('<img src="%s" style="width:64px;height:64px;object-fit:cover;'
                     'border-radius:8px;border:1px solid #eee;margin:4px 4px 0 0"/>'
                     % _e(u))
        cards.append(
            '<div style="border:1px solid #eee;border-radius:10px;padding:10px 12px;'
            'margin:8px 0">'
            '<div style="font-size:12px;color:#888">%s</div>'
            '<div style="color:#F5C320;font-size:13px;margin:2px 0">%s</div>'
            '<div style="font-size:13.5px;color:#333;line-height:1.5">%s</div>'
            '%s</div>' % (meta, stars, _e(r.get('text') or ''),
                          ('<div>%s</div>' % imgs) if imgs else ''))
    return ('<h4 style="margin:16px 0 8px">⭐ %s</h4>%s'
            % (head, ''.join(cards)))


def _async_enrich(dbname, ds_id, uid):
    """Enrich a dropship product in its own thread + cursor so the product-page
    request never blocks on the 3 live provider calls. Fail-soft."""
    from odoo import registry, api as _api
    try:
        db_registry = registry(dbname)
        with db_registry.cursor() as cr:
            env = _api.Environment(cr, uid, {})
            try:
                env['dropship.product'].sudo().browse(ds_id)._enrich_detail()
                cr.commit()
            except Exception:  # noqa: BLE001
                cr.rollback()
    except Exception:  # noqa: BLE001
        pass


def _enrich_world_detail(data, ds, lang):
    lang_ar = (lang or '').startswith('ar')
    base = _world_base_url()
    # Pull the full provider detail (reviews/specs/shipping) in the BACKGROUND
    # so opening a product is INSTANT — the page returns with whatever is
    # already stored, and the detail fills in for the next view. Only fire when
    # the record is stale (never blocks the response with 3 live API calls).
    try:
        ttl = int(request.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.detail_ttl_hours', 12) or 12)
        stale = True
        if ds.detail_synced:
            from datetime import datetime as _dt
            age = (_dt.now() - ds.detail_synced).total_seconds()
            stale = age > ttl * 3600
        if stale:
            import threading
            threading.Thread(
                target=_async_enrich,
                args=(ds.env.cr.dbname, ds.id, ds.env.uid),
                daemon=True).start()
    except Exception:  # noqa: BLE001
        pass
    try:
        ds._register_view()
        data['view_count'] = (ds.view_count or 0) + 1
        data['sold_count'] = ds.sold_display()
        data['orders_text'] = ds.orders_text or ''
        # live A/B title test: show (and count) the currently-serving variant
        if ds.ab_active and ds.title_en_b:
            data['title'] = ds._ab_title(lang_ar) or data.get('title')
    except Exception:  # noqa: BLE001
        pass
    specs = ds._ds_specs()
    ship = ds._ds_shipping()
    rev = ds._ds_review_summary()
    if specs:
        data['specifications'] = specs
    if rev:
        data['review_summary'] = rev
    reviews = ds._ds_reviews(limit=12)
    if reviews:
        # review photos are relative /dropship/media URLs — the app has no base
        # href, so make them absolute against the World host.
        for rv in reviews:
            if rv.get('images'):
                rv['images'] = [
                    (base + u if u.startswith('/') else u) for u in rv['images']]
        data['reviews'] = reviews
    # provider video (raw mp4) → inject into the detail gallery as the first
    # video, since it was never materialised into product.video.
    if ds.video_url:
        v = _hd_video_url(ds.video_url)
        vurl = (base + v) if v.startswith('/') else v
        vid_item = {
            'id': -(ds.id),
            'type': 'mp4',
            'video_url': vurl,
            'thumbnail': ds.image_url or '',
            'mime': 'video/mp4',
        }
        data['videos'] = [vid_item] + (data.get('videos') or [])
        data['has_video'] = True
        data['video_url'] = vurl
    # World default shipping label — never fall back to the KW '1-3 days';
    # a specific live-freight ETA (below) overrides this when available.
    _icp = ds.env['ir.config_parameter'].sudo()
    _dmin = int(_icp.get_param('uellow_dropship.world_ship_days_min', 10) or 10)
    _dmax = int(_icp.get_param('uellow_dropship.world_ship_days_max', 14) or 14)
    data['shipping_info_label'] = {
        'en': '\U0001F69A Ships from China \u00b7 %d\u2013%d days \u00b7 Free' % (_dmin, _dmax),
        'ar': '\U0001F69A \u064a\u064f\u0634\u062d\u0646 \u0645\u0646 \u0627\u0644\u0635\u064a\u0646 \u00b7 %d\u2013%d \u064a\u0648\u0645 \u00b7 \u0645\u062c\u0627\u0646\u064a' % (_dmin, _dmax),
    }
    if ship and ship[0].get('days_max'):
        o = ship[0]
        _free = o.get('free') or not o.get('cost')
        data['shipping_info_label'] = {
            'en': '\U0001F69A Ships from China · %d–%d days%s'
                  % (o['days_min'], o['days_max'], ' · Free' if _free else ''),
            'ar': '\U0001F69A يُشحن من الصين · %d–%d يوم%s'
                  % (o['days_min'], o['days_max'], ' · مجاني' if _free else ''),
        }
    # expose EVERY shipping method (not just the cheapest) so the app can offer
    # a selector; costs are converted to the shopper's display currency and the
    # provider/carrier name is brand-scrubbed. The chosen method's fee is applied
    # at checkout (see cart `world_shipping`).
    if ship:
        Rule = ds.env['dropship.text.rule']
        opts_out = []
        for o in ship:
            free = bool(o.get('free')) or not o.get('cost')
            name = Rule._apply_all(o.get('service') or 'Standard shipping') or 'Standard'
            opts_out.append({
                'code': (o.get('service') or 'std'),
                'name': name.strip() or 'Standard',
                'free': free,
                'price': _world_ship_price(o.get('cost') or 0.0, o.get('currency') or 'USD'),
                'days_min': o.get('days_min') or 0,
                'days_max': o.get('days_max') or 0,
                'eta_text': o.get('eta_text') or '',
                'tracking': bool(o.get('tracking')),
            })
        # cheapest / free first
        opts_out.sort(key=lambda x: (not x['free'], x['price']['amount']))
        data['shipping_options'] = opts_out
    desc_en = _absolutize(ds.description_html or '', base)
    desc_ar = _absolutize(ds.description_ar or ds.description_html or '', base)
    # description = the DESCRIPTION ONLY. Specs go to data['specifications'] and
    # reviews to data['reviews'] — the app renders those natively, so appending
    # a specs table + a reviews block INTO the description made them show twice
    # (and cluttered the description dialog). Keep the description clean.
    body_en = (desc_en or '')
    body_ar = (desc_ar or '')
    if body_en.strip() or body_ar.strip():
        data['description_html'] = {'en': body_en, 'ar': body_ar}


def _world_reviews_payload(ds, page=1, per_page=20):
    """Build the /products/<id>/reviews response for a dropship product from the
    cached AliExpress reviews, in the EXACT shape the app's native reviews UI
    expects ({reviews:[{author,rating,body,verified_purchase,photos,date}],
    summary:{avg,total,breakdown}}). Photos are absolutized to the World host.
    Returns (items, summary, meta) or None if the product has no reviews.
    """
    import json as _json
    try:
        rv = _json.loads(ds.reviews_json or '{}')
    except Exception:  # noqa: BLE001
        return None
    raw = rv.get('reviews') or []
    stats = rv.get('stats') or {}
    if not raw and not stats:
        return None
    base = _world_base_url()

    def _abs(u):
        return (base + u) if isinstance(u, str) and u.startswith('/') else u

    items = []
    for r in ds._ds_reviews(limit=len(raw) or 20):
        author = r.get('name') or 'Shopper'
        if r.get('country'):
            author = '%s · %s' % (author, r['country'])
        items.append({
            'id': 0,
            'rating': int(r.get('stars_full') or 5),
            'title': '',
            'body': r.get('text') or '',
            'author': author,
            'avatar': None,
            'date': r.get('date') or None,
            'verified_purchase': True,   # real AliExpress buyers
            'helpful_count': 0,
            'photos': [_abs(u) for u in (r.get('images') or [])],
            'pending': False,
            'video_url': '',
            'vendor_reply': '',
        })
    total = int(stats.get('total') or len(items) or 0)

    def _n(k):
        try:
            return int(stats.get(k) or 0)
        except (TypeError, ValueError):
            return 0
    # AliExpress stats give five/four/three(neutral)/negative(1-2★ combined).
    breakdown = {'5': _n('five'), '4': _n('four'), '3': _n('three'),
                 '2': 0, '1': _n('negative')}
    try:
        avg = round(float(stats.get('avg') or ds.rating or 0.0), 1)
    except (TypeError, ValueError):
        avg = round(ds.rating or 0.0, 1)
    summary = {'avg': avg, 'total': total, 'breakdown': breakdown}
    # simple slice pagination over the (≤20) cached reviews
    try:
        page = max(1, int(page))
        per_page = max(1, int(per_page))
    except (TypeError, ValueError):
        page, per_page = 1, 20
    start = (page - 1) * per_page
    paged = items[start:start + per_page]
    meta = {'page': page, 'per_page': per_page, 'total': len(items)}
    return paged, summary, meta


def _install_detail_patch():
    from odoo.addons.uellow_mobile_manager.controllers.api_v2 import (
        products as _pmod,
    )
    orig = _pmod.serialize_product_full
    if getattr(orig, '_world_patched', False):
        return

    def _patched(product, lang='en_US'):
        data = orig(product, lang)
        if not data:
            return data
        try:
            if getattr(product, 'is_dropship', False) and product.dropship_product_id:
                _enrich_world_detail(data, product.dropship_product_id.sudo(), lang)
        except Exception:  # noqa: BLE001 - never break the product screen
            pass
        return data

    _patched._world_patched = True
    _pmod.serialize_product_full = _patched


_install_detail_patch()


# ── fill the card rating from the provider (listing social proof) ────────────
# The app card already renders `rating:{avg,count}`, but for dropship products
# the Odoo rating_avg/rating_count are 0 (no on-site reviews). Fill them from the
# provider's rating/evaluation-count so the grid shows real stars. Patches the
# module-global serialize_product_card (used by feed/list/search inside
# products.py) AND rebinds app_bridge's own imported name (used by
# _world_category_products).
def _install_card_patch():
    from odoo.addons.uellow_mobile_manager.controllers.api_v2 import (
        products as _pmod,
    )
    orig = _pmod.serialize_product_card
    if getattr(orig, '_world_patched', False):
        return

    def _patched(product, lang='en_US'):
        card = orig(product, lang)
        try:
            if card and getattr(product, 'is_dropship', False) \
                    and product.dropship_product_id:
                ds = product.dropship_product_id.sudo()
                if ds.rating:
                    card['rating'] = {'avg': round(ds.rating, 1),
                                      'count': ds.review_count or 0}
                # World flag → the app card shows an honest "ships worldwide"
                # line instead of the Kuwait "delivery in hours" line.
                card['world'] = True
                # live A/B test: card shows the same time-bucket variant title
                # as the detail page, so the experiment is consistent.
                if ds.ab_active and ds.title_en_b:
                    _t = ds._ab_title((lang or '').startswith('ar'))
                    if _t:
                        card['title'] = _t
                # video badge: the dropship video is a raw mp4 on video_url
                # (never materialised into product.video), so the standard
                # has_video is False — set it from the provider video here.
                if ds.video_url:
                    card['has_video'] = True
                # real engagement numbers for the card ticker (views + sold);
                # the on-site product.template counters are 0 for dropship.
                if ds.view_count:
                    card['view_count'] = ds.view_count
                sold = ds.sold_display()
                if sold:
                    card['sold_count'] = sold
        except Exception:  # noqa: BLE001
            pass
        return card

    _patched._world_patched = True
    _pmod.serialize_product_card = _patched
    globals()['serialize_product_card'] = _patched


_install_card_patch()


# ── World scope: every public product query returns dropship products only ───
# Kuwait products are website-AGNOSTIC (website_id=False), so the shared
# `_domain_published_for_app` leaks them onto World too — they showed up in
# World search, explore, bestsellers, etc. Here we wrap that helper so on World
# it also requires is_dropship=True. Because the callers import the name INTO
# their own module namespace (`from .products import _domain_published_for_app`),
# a single rebind on products.py is not enough — we rebind it in EVERY module
# that imported it (search, categories, vendors, videos).
def _install_world_domain_patch():
    from odoo.addons.uellow_mobile_manager.controllers.api_v2 import (
        products as _pmod, search as _smod, categories as _cmod,
        vendors as _vmod, videos as _vidmod,
    )
    orig = _pmod._domain_published_for_app
    if getattr(orig, '_world_patched', False):
        return

    def _patched(include_oos=False):
        dom = list(orig(include_oos=include_oos))
        try:
            if _is_world():
                dom.append(('is_dropship', '=', True))
                # optional: only show products that ship to the customer's
                # country. Products with no coverage data yet are NOT hidden.
                cc = _world_ship_country()
                if cc:
                    dom += ['|',
                            ('dropship_product_id.ship_country_ids', '=', False),
                            ('dropship_product_id.ship_country_ids.code', '=', cc)]
        except Exception:  # noqa: BLE001
            pass
        return dom

    _patched._world_patched = True
    _pmod._domain_published_for_app = _patched
    for _m in (_smod, _cmod, _vmod, _vidmod):
        if getattr(_m, '_domain_published_for_app', None) is not None:
            _m._domain_published_for_app = _patched


_install_world_domain_patch()


# ── World home: top "tab-nav" strip = REAL dropship categories, linked ───────
# The builder's tab-nav block carries static tabs in its props. On World we
# overwrite them with the most-populated real dropship categories, each linked
# to its World category products screen (tap → goCollection(dropship.category id)).
def _world_tabnav_tabs(env, lang):
    DC = env['dropship.category'].sudo()
    ar_code = _ar_code()

    def _tab(c):
        en = c.with_context(lang='en_US').name or c.code
        ar = c.with_context(lang=ar_code).name or en
        return {
            'labelEn': en,
            'labelAr': ar,
            'link': {'type': 'category', 'value': str(c.id)},
        }

    # 1) admin-configured categories (Settings → Home Tab Categories) win, in
    #    the exact order the admin picked them.
    raw = (env['ir.config_parameter'].sudo().get_param(
        'uellow_dropship.tabnav_category_ids') or '')
    ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
    if ids:
        cats = DC.browse(ids).exists()
        tabs = [_tab(c) for c in cats]
        if tabs:
            return tabs
    # 2) fallback: auto top-10 root categories by product count.
    counts = _ds_counts()
    roots = DC.search([('parent_id', '=', False)], order='sequence asc, name asc')
    scored = [(_node_count(c, counts), c) for c in roots]
    scored = [(n, c) for (n, c) in scored if n > 0]
    scored.sort(key=lambda x: -x[0])
    return [_tab(c) for _n, c in scored[:10]]


# ── World scope: EVERY home block resolver returns dropship products only ────
# The block resolvers (explore-more, bestsellers, promo rails, cats-grid…) build
# their own domain via the shared _site_dom() helper — NOT the mobile_manager
# _domain_published_for_app that the other World patch covers. On World we add
# is_dropship=True to _site_dom so home blocks never mix in Kuwait products.
def _install_world_sitedom_patch():
    from odoo.addons.uellow_mobile_pages.models import block_resolver as _br
    orig = getattr(_br, '_site_dom', None)
    if orig is None or getattr(orig, '_world_patched', False):
        return

    def _patched(env):
        dom = list(orig(env))
        try:
            if _is_world():
                dom = dom + [('is_dropship', '=', True)]
        except Exception:  # noqa: BLE001
            pass
        return dom

    _patched._world_patched = True
    _br._site_dom = _patched


_install_world_sitedom_patch()


def _install_world_tabnav_patch():
    from odoo.addons.uellow_mobile_pages.models import block_resolver as _br
    orig = _br.resolve_block
    if getattr(orig, '_world_tabnav_patched', False):
        return

    def _patched(env, block, lang, ctx=None):
        out = orig(env, block, lang, ctx=ctx)
        try:
            if out.get('kind') == 'tab-nav' and _is_world():
                tabs = _world_tabnav_tabs(env, lang)
                if tabs:
                    props = dict(out.get('props') or {})
                    props['tabs'] = tabs
                    out = dict(out)
                    out['props'] = props
        except Exception:  # noqa: BLE001 - never break page rendering
            pass
        return out

    _patched._world_tabnav_patched = True
    _br.resolve_block = _patched


_install_world_tabnav_patch()


# ── World scope: search side-panels (categories/brands/vendors) ──────────────
# The main products list is scoped by the domain patch above; the search
# endpoint also returns matched Kuwait categories/brands/vendors, which are
# meaningless on World. Blank those on World so search shows dropship products
# (+ World taxonomy handled elsewhere) only.
class WorldSearchAPI(MobileSearchAPI):

    def search(self, **kw):
        resp = super().search(**kw)
        if not _is_world():
            return resp
        try:
            import json as _json
            payload = _json.loads(resp.data)
            if payload.get('success') and isinstance(payload.get('data'), dict):
                payload['data']['categories'] = []
                payload['data']['brands'] = []
                payload['data']['vendors'] = []
                resp.data = _json.dumps(payload).encode()
        except Exception:  # noqa: BLE001 - never break search
            pass
        return resp
