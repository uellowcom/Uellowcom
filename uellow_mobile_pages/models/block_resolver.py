# -*- coding: utf-8 -*-
"""Block resolver — turns a designer-saved block into a renderable payload.

The builder stores `props` like `{titleEn, source, limit, category_ids}`. The
mobile app expects a `data` payload it can dump straight into widgets. The
resolver bridges the two: for every block kind that surfaces real records
(categories, products, vendors, sliders, banners), we query the DB
server-side and embed the result inside the block JSON the public API
returns.

Each resolver receives:
    env   — odoo env (sudo'd)
    props — the block's `props` dict (designer's settings)
    lang  — short lang code ('en', 'ar', ...) for label flattening
    block — the full block dict (rarely needed, but useful for kind-aware
            decisions)

Each resolver returns a dict that gets merged into the block under `data`.
"""
import logging

_logger = logging.getLogger(__name__)


def _img(env, model, rec_id, field='image_512', unique=None):
    from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import img_url
    try:
        return img_url(model, rec_id, field, unique=unique)
    except Exception:
        return None


def _label(rec, field='name', lang='en'):
    """Return translated string in the requested language with English
    fallback. Works whether translation is loaded or not."""
    try:
        # Try the requested lang first
        if lang and lang != 'en':
            val = rec.with_context(lang=_full_lang(rec.env, lang))[field]
            if val:
                return val
    except Exception:
        pass
    return rec[field] or ''


def _full_lang(env, short):
    rec = env['res.lang'].sudo().search(
        [('active', '=', True), ('code', '=like', short + '%')], limit=1)
    return rec.code if rec else 'en_US'


# ─── Categories ────────────────────────────────────────────────────────────

def resolve_categories(env, props, lang, block=None):
    """Returns a list of {id, name, slug, icon_url}."""
    source = (props.get('source') or 'auto').strip()
    limit = int(props.get('limit') or 12)
    Cat = env['product.public.category'].sudo()
    if source == 'manual' and props.get('category_ids'):
        try:
            ids = [int(x) for x in props['category_ids']]
        except Exception:
            ids = []
        cats = Cat.browse(ids).exists()
    else:
        # `auto` = top-level categories
        cats = Cat.search([('parent_id', '=', False)], limit=limit)
    out = []
    for c in cats:
        out.append({
            'id': c.id,
            'name': _label(c, 'name', lang),
            'slug': getattr(c, 'website_url', None) or '',
            'icon_url': _img(env, 'product.public.category', c.id, 'image_128',
                             unique=c.write_date),
        })
    return {'items': out}


# ─── Products ──────────────────────────────────────────────────────────────

def resolve_products(env, props, lang, block=None):
    """Returns {items: [{id, name, slug, price, image, ...}, ...]}.

    The block kind hints at the source if `source` isn't set:
        block.kind == 'flash'        → discounted products
        block.kind == 'bestsellers'  → top-selling last 30 days
        block.kind == 'rec-ai'       → curated (Beena) — falls back to bestsellers
        block.kind == 'recent'       → can't resolve without a user; empty
    """
    kind = (block or {}).get('kind', 'products')
    source = (props.get('source') or '').strip()
    # Implicit source from kind
    if not source:
        if kind == 'flash':        source = 'discounted'
        elif kind == 'bestsellers':source = 'bestsellers'
        elif kind == 'rec-ai':     source = 'bestsellers'
        elif kind == 'recent':     source = 'recent'
        elif kind == 'grid':       source = 'newest'
        elif kind == 'new-user':   source = 'discounted'
        else:                      source = 'newest'

    limit = int(props.get('limit') or 12)
    Tmpl = env['product.template'].sudo()
    base_dom = [('is_published', '=', True),
                ('sale_ok', '=', True),
                ('website_published', '=', True)]
    recs = Tmpl

    if source == 'manual' and props.get('product_ids'):
        try:
            ids = [int(x) for x in props['product_ids']]
        except Exception:
            ids = []
        recs = Tmpl.browse(ids).exists()

    elif source == 'collection' and props.get('category_id'):
        recs = Tmpl.search(base_dom + [
            ('public_categ_ids', 'in', [int(props['category_id'])])
        ], limit=limit)

    elif source == 'vendor' and props.get('vendor_id'):
        # Multivendor: products may have a vendor_id m2o or similar
        dom = list(base_dom)
        if 'vendor_id' in Tmpl._fields:
            dom.append(('vendor_id', '=', int(props['vendor_id'])))
            recs = Tmpl.search(dom, limit=limit)
        else:
            recs = Tmpl.search(base_dom, limit=limit)

    elif source == 'discounted':
        # v2.1.76 — when a "Minimum discount %" filter is set, the small
        # `limit` window made the filter look broken (it only kept the few
        # high-discount items that happened to be in the first N rows).
        # Fetch a WIDER pool here; the post-filter below trims to `limit`.
        try:
            _min_d = int(props.get('min_discount_pct') or 0)
        except Exception:
            _min_d = 0
        _pool = min(max(limit * 12, 200), 600) if _min_d > 0 else limit
        recs = Tmpl.search(
            base_dom + [('compare_list_price', '>', 0)],
            order='write_date desc', limit=_pool)
        if not recs:
            # Fallback: any recent published product
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'flash_sale':
        # v2.0.62 — link the block to live uellow.flash.sale records.
        # Returns the union of products across the picked sales plus
        # metadata (timer end + max_quantity + vendor) so the Flutter
        # widget can show progress + vendor name + urgency.
        FlashSale = env.get('uellow.flash.sale')
        if not FlashSale:
            return {'items': []}
        Fs = FlashSale.sudo()
        dom_fs = [('state', '=', 'active')]
        if props.get('flash_sale_ids'):
            try:
                ids = [int(x) for x in props['flash_sale_ids']]
                dom_fs = [('id', 'in', ids)]
            except Exception:
                pass
        sales = Fs.search(dom_fs, order='end_datetime asc')
        prod_ids = []
        meta_by_prod = {}
        earliest_end = None
        flash_label_en = ''
        flash_label_ar = ''
        for s in sales:
            if not earliest_end or (s.end_datetime and s.end_datetime < earliest_end):
                earliest_end = s.end_datetime
                flash_label_en = s.name or ''
                flash_label_ar = s.name_ar or s.name or ''
            for p in s.product_ids:
                if p.id not in meta_by_prod:
                    prod_ids.append(p.id)
                    meta_by_prod[p.id] = {
                        'flash_sale_id': s.id,
                        'flash_sale_name': s.name,
                        'flash_discount_pct': s.discount_pct,
                        'flash_units_sold': s.units_sold,
                        'flash_max_quantity': s.max_quantity,
                        'flash_end_datetime':
                            s.end_datetime.isoformat() if s.end_datetime else '',
                        'vendor_name': (s.vendor_id.name
                                        if s.vendor_id else ''),
                    }
        recs = Tmpl.browse(prod_ids[:limit]).exists()
        # Stash meta + earliest end so resolver below uses it
        env.context.get('_flash_meta_stash', {}).update(meta_by_prod)
        return {
            'items': [dict(_product_brief(env, p, lang),
                           **meta_by_prod.get(p.id, {}))
                      for p in recs],
            'flash_end_datetime':
                earliest_end.isoformat() if earliest_end else '',
            'flash_label': {'en': flash_label_en, 'ar': flash_label_ar},
            'flash_count': len(sales),
        }

    elif source == 'bestsellers':
        # v2.1.24 — REAL bestsellers from the daily rank table
        # (uellow_product_rank). Optional props.category_id narrows the
        # ladder to one category ("Best of Smart Watches" block).
        recs = Tmpl.browse([])
        try:
            Rank = env.get('uellow.product.rank')
            if Rank is not None:
                cat_id = props.get('category_id')
                recs = Rank.sudo().top_products(
                    category_id=int(cat_id) if cat_id else None,
                    website_id=None, limit=limit)
                recs = recs.filtered(lambda p: p.is_published)
        except Exception:
            recs = Tmpl.browse([])
        if not recs:
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'newest':
        recs = Tmpl.search(base_dom, order='create_date desc', limit=limit)

    elif source == 'promotion':
        # v2.1.30 — products of one promotion campaign (props.promotion_id).
        # v2.1.37 — also accepts promotion_ids (multi) and, for the FLASH
        # block, returns the campaign timer + label so the countdown and
        # title come automatically from the backend campaign.
        recs = Tmpl.browse([])
        promos = None
        try:
            pids = [int(x) for x in (props.get('promotion_ids') or [])]
            if not pids and props.get('promotion_id'):
                pids = [int(props['promotion_id'])]
            Line = env.get('mobile.promotion.line')
            Promo = env.get('mobile.app.promotion')
            if pids and Line is not None:
                lines = Line.sudo().search([
                    ('promotion_id', 'in', pids),
                    ('state', '=', 'approved')], limit=limit * 2)
                recs = lines.mapped('product_tmpl_id').filtered(
                    lambda p: p.active and p.is_published)[:limit]
                if Promo is not None:
                    promos = Promo.sudo().browse(pids).exists()
        except Exception:
            recs = Tmpl.browse([])
        if (block or {}).get('kind') == 'flash' and promos:
            earliest = min((p.date_to for p in promos if p.date_to),
                           default=False)
            first = promos[:1]
            return {
                'items': [_product_brief(env, p, lang) for p in recs],
                'flash_end_datetime':
                    earliest.isoformat() if earliest else '',
                'flash_label': {
                    'en': first.label_en or first.name or '',
                    'ar': first.label_ar or first.label_en or '',
                },
                'flash_count': len(promos),
            }
        if not recs:
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'price_drops':
        # v2.1.25 — products whose price recently DROPPED (internal price
        # intelligence). props.days narrows the window (default 14).
        recs = Tmpl.browse([])
        try:
            Hist = env.get('uellow.price.history')
            if Hist is not None:
                recs = Hist.sudo().top_drops(
                    days=int(props.get('days') or 14), limit=limit)
        except Exception:
            recs = Tmpl.browse([])
        if not recs:
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'free_shipping':
        # v2.1.46 — a proper SQL domain. The old code scanned only the
        # NEWEST limit*3 products and filtered in Python, so a catalog
        # whose free-shipping items aren't recent showed just 1-2 of
        # them. Now: product flag OR tag flag OR (category-or-parent
        # flag, via child_of on the marked categories).
        recs = Tmpl.browse([])
        if 'free_shipping' in Tmpl._fields:
            try:
                ors = [('free_shipping', '=', True)]
                if 'product_tag_ids' in Tmpl._fields:
                    ors.append(
                        ('product_tag_ids.free_shipping', '=', True))
                free_cats = env['product.public.category'].sudo().search(
                    [('free_shipping', '=', True)])
                if free_cats:
                    ors.append(
                        ('public_categ_ids', 'child_of', free_cats.ids))
                dom_free = ['|'] * (len(ors) - 1) + ors
                recs = Tmpl.search(base_dom + dom_free,
                                   order='create_date desc', limit=limit)
            except Exception:
                recs = Tmpl.browse([])
        if not recs:
            # Legacy fallback — python-side walk over a wider window.
            all_recs = Tmpl.search(base_dom, order='create_date desc',
                                   limit=max(limit * 10, 200))
            filtered = []
            for prod in all_recs:
                if hasattr(prod, '_is_free_shipping') \
                        and prod._is_free_shipping():
                    filtered.append(prod.id)
                    if len(filtered) >= limit:
                        break
            recs = Tmpl.browse(filtered)

    elif source == 'recent':
        # Personal — can't resolve at page-fetch time; let the app fall
        # back to its own /recently-viewed endpoint.
        return {'items': [], 'fetch_endpoint': 'recently-viewed'}

    else:
        recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    items = [_product_brief(env, p, lang) for p in recs]
    # v2.0.67 — optional post-filter + sort for Discount Strip & friends
    try:
        min_disc = int(props.get('min_discount_pct') or 0)
    except Exception:
        min_disc = 0
    if min_disc > 0:
        items = [x for x in items if (x.get('discount_pct') or 0) >= min_disc]
        # we widened the fetch pool above; trim back to the block's limit.
        items = items[:limit]
    sort_by = (props.get('sort') or '').strip()
    if sort_by == 'discount_desc':
        items.sort(key=lambda x: -(x.get('discount_pct') or 0))
    elif sort_by == 'price_asc':
        items.sort(key=lambda x: (x.get('price') or {}).get('amount') or 0)
    elif sort_by == 'price_desc':
        items.sort(key=lambda x: -((x.get('price') or {}).get('amount') or 0))
    # 'newest' is already the default order from search
    return {'items': items}


def _product_brief(env, p, lang):
    # v2.1.33 — reuse the FULL api_v2 card serializer when an HTTP
    # request context exists (rank, promo coin, price trend, cart adds,
    # video flag, real ratings/stock) so builder blocks render the same
    # rich cards as the category page. Falls back to the brief shape.
    try:
        from odoo.http import request as _rq
        if _rq:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2 \
                .products import serialize_product_card
            card = serialize_product_card(p, lang)
            if card:
                return card
    except Exception:
        pass
    return _product_brief_fallback(env, p, lang)


def _product_brief_fallback(env, p, lang):
    price = p.list_price
    compare = getattr(p, 'compare_list_price', 0.0) or 0.0
    cur = p.currency_id
    nm_en = p.with_context(lang='en_US').name or p.name or ''
    nm_ar = ''
    try:
        ar_full = _full_lang(env, 'ar')
        nm_ar = p.with_context(lang=ar_full).name or nm_en
    except Exception:
        nm_ar = nm_en
    return {
        'id': p.id,
        # Bilingual shape so the Flutter UellowProductCard parser accepts it
        'name': {'en': nm_en, 'ar': nm_ar},
        'slug': getattr(p, 'website_url', '') or '',
        'image': _img(env, 'product.template', p.id, 'image_512',
                      unique=p.write_date),
        'price': {
            'amount': float(price or 0),
            'currency': cur.name,
            'symbol': cur.symbol,
            'digits': cur.decimal_places,
        },
        'compare_price': {
            'amount': float(compare),
            'currency': cur.name,
            'symbol': cur.symbol,
            'digits': cur.decimal_places,
        } if compare and compare > price else None,
        'discount_pct': int(round(100 * (compare - price) / compare))
                         if compare and compare > price else 0,
        'in_stock': True,
        'is_published': True,
        'badges': [],
        'rating': {'avg': 0.0, 'count': 0},
        'vendor': None,
        'allow_out_of_stock_order': True,
        'has_video': False,
    }


# ─── Vendors ───────────────────────────────────────────────────────────────

def resolve_vendors(env, props, lang, block=None):
    """Returns top vendors (or manually picked ones)."""
    limit = int(props.get('limit') or 8)
    try:
        Vendor = env['uellow.vendor'].sudo()
    except KeyError:
        return {'items': []}
    if (props.get('source') or '') == 'manual' and props.get('vendor_ids'):
        try:
            ids = [int(x) for x in props['vendor_ids']]
        except Exception:
            ids = []
        recs = Vendor.browse(ids).exists()
    else:
        # Don't filter on state — many existing vendors are stateless.
        # Order by most-recently-active.
        recs = Vendor.search([], order='write_date desc', limit=limit)
    out = []
    for v in recs:
        # Vendor display name lives either on the linked partner or as a
        # computed `display_name` field on the vendor record itself.
        nm = ''
        if 'name' in v._fields:
            nm = v.name or ''
        if not nm and 'display_name' in v._fields:
            nm = v.display_name or ''
        if not nm and 'partner_id' in v._fields and v.partner_id:
            nm = v.partner_id.name or ''
        logo = None
        for field in ('logo_image', 'image_128', 'logo', 'image'):
            if field in v._fields and v[field]:
                logo = _img(env, 'uellow.vendor', v.id, field, unique=v.write_date)
                break
        # Fall back to partner's image if vendor record has none
        if not logo and 'partner_id' in v._fields and v.partner_id and v.partner_id.image_128:
            logo = _img(env, 'res.partner', v.partner_id.id, 'image_128',
                        unique=v.partner_id.write_date)
        rating = None
        if 'rating_avg' in v._fields and v.rating_avg:
            rating = float(v.rating_avg)
        out.append({
            'id': v.id,
            'name': nm,
            'slug': getattr(v, 'slug', '') or '',
            'logo': logo,
            'tier': getattr(v, 'tier', '') or '',
            'rating': rating,
        })
    return {'items': out}


# ─── Sliders / banners — resolve images ────────────────────────────────────

def resolve_hero(env, props, lang, block=None):
    """Hero blocks may reference an uploaded image stored as ir.attachment.
    If `image_attachment_id` is set, expose its public URL."""
    out = {}
    att_id = props.get('image_attachment_id')
    if att_id:
        try:
            att = env['ir.attachment'].sudo().browse(int(att_id))
            if att.exists():
                from odoo.addons.uellow_mobile_manager.controllers.api_v2._common \
                    import base_url
                out['image_url'] = f"{base_url()}/web/image/{att.id}"
        except Exception:
            pass
    # Carousel block — reuse mobile.slider records if no manual list set
    if (block or {}).get('kind') == 'carousel' and not props.get('slides'):
        Slider = env['mobile.slider'].sudo()
        recs = Slider.search([], limit=6)
        out['slides'] = [{
            'id': s.id,
            'image_url': _img(env, 'mobile.slider', s.id, 'image_1920',
                              unique=s.write_date),
            'link': s.url if 'url' in s._fields else '',
        } for s in recs]
    return out


# ─── Dispatcher ────────────────────────────────────────────────────────────

def resolve_welcome_deal(env, props, lang, block=None):
    """Welcome deal — 2x2 product grid. Resolves to 4 product images.
    Picks discounted products by default, or manual list if set."""
    limit = 4
    Tmpl = env['product.template'].sudo()
    base_dom = [('is_published', '=', True),
                ('sale_ok', '=', True),
                ('website_published', '=', True)]
    if props.get('product_ids'):
        try:
            ids = [int(x) for x in props['product_ids']][:limit]
        except Exception:
            ids = []
        recs = Tmpl.browse(ids).exists()
    else:
        recs = Tmpl.search(base_dom + [('compare_list_price', '>', 0)],
                           order='write_date desc', limit=limit)
        if not recs:
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)
    return {'products': [_product_brief(env, p, lang) for p in recs]}


def resolve_quick_pills(env, props, lang, block=None):
    """Quick pills items already live in props; nothing to fetch.
    We just pass them through so the Flutter side can render."""
    return {}


def resolve_mini_cats(env, props, lang, block=None):
    """Mini-cats — each card may reference a category by id. We expose
    the resolved category image_url so the card uses a real photo if the
    designer didn't override `image_url` in the card."""
    out_cards = []
    for c in (props.get('cards') or []):
        cc = dict(c)
        if not cc.get('image_url') and cc.get('category_id'):
            try:
                cat = env['product.public.category'].sudo().browse(int(cc['category_id']))
                if cat.exists():
                    cc['image_url'] = _img(env, 'product.public.category', cat.id,
                                           'image_512', unique=cat.write_date)
            except Exception:
                pass
        out_cards.append(cc)
    return {'resolved_cards': out_cards}


def _get_free_ship_threshold(env):
    """Read the free-shipping threshold once per request. Without this,
    `_enrich_with_badges` would call env['mobile.app.setting'].search([])
    for every product in the explore feed — 12 redundant DB hits per page
    under heavy bot traffic (the v2.0.37 regression that made the server
    slow). We stash the value on the request object so each enrichment
    loop pays the cost once."""
    try:
        req = env.context.get if False else None  # unused — keep linter calm
    except Exception:
        pass
    try:
        from odoo.http import request
        if request is not None:
            cached = getattr(request, '_uellow_free_ship_thr', None)
            if cached is not None:
                return cached
            s = env['mobile.app.setting'].sudo().search([], limit=1)
            thr = getattr(s, 'free_shipping_threshold', 0) or 0
            request._uellow_free_ship_thr = thr
            return thr
    except Exception:
        pass
    # Not in a request context — read once directly (cron, tests, etc.)
    try:
        s = env['mobile.app.setting'].sudo().search([], limit=1)
        return getattr(s, 'free_shipping_threshold', 0) or 0
    except Exception:
        return 0


def _enrich_with_badges(env, brief, product, is_anchor_new_days=7,
                        free_ship_threshold=None):
    """Mutate brief in-place to add discovery badges. Logic kept fast —
    we only check fields already loaded on `product`. Callers in a tight
    loop should pass `free_ship_threshold` explicitly to skip the
    per-product settings lookup."""
    import datetime as _dt
    badges = []
    # 🔥 Hot — discount-based heuristic
    try:
        if product.compare_list_price and product.compare_list_price > product.list_price:
            disc = 100 * (product.compare_list_price - product.list_price) / product.compare_list_price
            if disc >= 30:
                badges.append({'kind': 'hot', 'label_en': '🔥 Hot deal',     'label_ar': '🔥 صفقة ساخنة', 'color': '#E63946'})
            elif disc >= 15:
                badges.append({'kind': 'deal','label_en': '💯 Best deal',    'label_ar': '💯 أفضل عرض', 'color': '#F5C320'})
    except Exception:
        pass
    # ✨ New — created in last N days
    try:
        if product.create_date:
            age = (_dt.datetime.utcnow() - product.create_date).days
            if age <= is_anchor_new_days:
                badges.append({'kind': 'new', 'label_en': '✨ New',          'label_ar': '✨ جديد', 'color': '#1F8A40'})
    except Exception:
        pass
    # 🚚 Free shipping — uses pre-fetched threshold, no per-call DB hit
    try:
        threshold = free_ship_threshold if free_ship_threshold is not None else _get_free_ship_threshold(env)
        if threshold and product.list_price >= threshold:
            badges.append({'kind': 'free_ship', 'label_en': '🚚 Free ship', 'label_ar': '🚚 شحن مجاني', 'color': '#1D6FB7'})
    except Exception:
        pass
    brief['badges'] = badges + (brief.get('badges') or [])


def resolve_explore_more(env, props, lang, block=None):
    """Explore More v2 — full discovery suite. Returns:
        items[]          — first batch, with badges per product
        sponsored_ids[]  — designer-picked products to weave in at every Nth slot
        category_chips[] — top categories present in the result set
        trending_stat    — server-computed stats string (e.g. "+47% sold this week")
        why_caption      — bilingual "why you see this" text
        seed, next_page, has_more, total_estimate
    """
    import hashlib, datetime, random as _rnd

    per_page  = max(4, min(int(props.get('per_page') or 12), 40))
    source    = (props.get('source') or 'random').strip()
    sort      = (props.get('sort')   or 'best_match').strip()
    cat_id    = props.get('category_id')
    chip_cat  = props.get('active_chip_id')  # client may pass back narrowed filter
    sponsored = [int(x) for x in (props.get('sponsored_ids') or []) if str(x).isdigit()]

    Tmpl = env['product.template'].sudo()
    base_dom = [('is_published', '=', True),
                ('sale_ok', '=', True),
                ('website_published', '=', True)]
    # Active chip beats designer's source category
    if chip_cat:
        try:
            base_dom.append(('public_categ_ids', 'in', [int(chip_cat)]))
        except Exception:
            pass
    elif source == 'category' and cat_id:
        try:
            base_dom.append(('public_categ_ids', 'in', [int(cat_id)]))
        except Exception:
            pass
    elif source == 'discounted':
        base_dom.append(('compare_list_price', '>', 0))

    # Choose the order based on sort (overrides source's natural order)
    if sort == 'newest' or source == 'newest':
        order = 'create_date desc'
    elif sort == 'price_asc':
        order = 'list_price asc'
    elif sort == 'price_desc':
        order = 'list_price desc'
    elif sort == 'top_rated':
        order = 'write_date desc'  # placeholder — needs rating field
    elif source == 'bestsellers':
        order = 'write_date desc'
    else:
        order = None  # random handled below

    if order:
        recs = Tmpl.search(base_dom, order=order, limit=per_page)
    else:
        all_ids = Tmpl.search(base_dom).ids
        if not all_ids:
            return {'items': [], 'has_more': False, 'seed': 1, 'next_page': 2}
        day_key = datetime.date.today().isoformat().encode()
        h = int(hashlib.sha256(day_key).hexdigest()[:8], 16)
        idx = [(i + h) % len(all_ids) for i in range(len(all_ids))]
        permuted = [all_ids[i] for i in idx]
        recs = Tmpl.browse(permuted[:per_page]).exists()

    # Build product briefs + enrich with badges (threshold fetched once)
    free_ship_thr = _get_free_ship_threshold(env)
    items = []
    for p in recs:
        brief = _product_brief(env, p, lang)
        _enrich_with_badges(env, brief, p, free_ship_threshold=free_ship_thr)
        items.append(brief)

    # Sponsored slots — weave in designer's picks
    sponsored_briefs = []
    if sponsored:
        sp_recs = Tmpl.browse(sponsored).exists()
        for sp in sp_recs:
            sb = _product_brief(env, sp, lang)
            sb['sponsored'] = True
            sb['badges'] = [{'kind':'sponsored','label_en':'✨ Sponsored','label_ar':'✨ ممول','color':'#6E4AB0'}]
            sponsored_briefs.append(sb)

    # Category chips — top 5 categories present in this result set
    cat_counts = {}
    for p in recs:
        for c in p.public_categ_ids[:3]:
            cat_counts[(c.id, c.name)] = cat_counts.get((c.id, c.name), 0) + 1
    chips = sorted(cat_counts.items(), key=lambda kv: -kv[1])[:6]
    category_chips = [{'id': k[0], 'name': k[1], 'count': v} for (k, v) in chips]

    # "Why you see this" copy — varies by source mode
    why_map = {
        'random':      ('Random picks tailored to your country',  'مختارة لك حسب موقعك'),
        'discounted':  ('Active discounts ending soon',            'تخفيضات نشطة'),
        'newest':      ('Just landed this week',                   'وصلت حديثاً'),
        'bestsellers': ('Most popular in your area',               'الأكثر شعبية لديك'),
        'for_me':      ('Based on items you viewed recently',      'مبني على ما شاهدته مؤخراً'),
        'category':    ('Curated for this category',               'مختار لهذا القسم'),
    }
    en, ar = why_map.get(source, why_map['random'])
    why_caption = {'en': en, 'ar': ar}

    # Trending stat — fake-but-believable engagement copy (for now)
    week_seed = int(hashlib.md5(datetime.date.today().isoformat().encode()).hexdigest()[:4], 16)
    trending_pct = 20 + (week_seed % 60)
    trending_stat = {
        'en': f'🔥 +{trending_pct}% browsed this week',
        'ar': f'🔥 +{trending_pct}% تصفّحوا هذا الأسبوع',
    }

    return {
        'items': items,
        'sponsored': sponsored_briefs,
        'category_chips': category_chips,
        'trending_stat': trending_stat,
        'why_caption': why_caption,
        'seed': abs(hash(str(cat_id or '') + source + sort)) & 0x7FFFFFFF,
        'next_page': 2,
        'has_more': len(recs) >= per_page,
        'total_estimate': Tmpl.search_count(base_dom),
    }


def resolve_slider(env, props, lang, block=None):
    """Resolve slider — pass through slides; nothing to fetch except
    optional category/product images embedded in image_url."""
    return {'slides': props.get('slides') or []}


def resolve_passthrough(env, props, lang, block=None):
    """Generic pass-through for blocks whose data lives entirely in props."""
    return {}


def resolve_reels_strip(env, props, lang, block=None):
    """v2.0.90 — collect trending products that have a video so the home
    `reels-strip` block can render circular thumbnails the user taps to
    jump into the full Reels feed."""
    Tmpl = env['product.template'].sudo()
    limit = int(props.get('limit') or 8)
    base_dom = [('is_published', '=', True), ('active', '=', True)]
    # Cheap pre-filter when the cached flag exists
    if 'has_product_video' in Tmpl._fields:
        base_dom.append(('has_product_video', '=', True))
    order = 'sales_count desc, write_date desc' \
        if 'sales_count' in Tmpl._fields else 'write_date desc'
    candidates = Tmpl.search(base_dom, order=order, limit=limit * 4)
    items = []
    for p in candidates:
        # Skip products that are out of stock and not "continue selling".
        if not getattr(p, 'allow_out_of_stock_order', True):
            storable = getattr(p, 'is_storable', None)
            if storable is None:
                storable = (getattr(p, 'type', '') == 'product')
            if storable:
                try:
                    if (p.virtual_available or 0) <= 0:
                        continue
                except Exception:
                    pass
        try:
            vids = getattr(p, 'video_ids', None) or getattr(p, 'product_video_ids', None)
        except Exception:
            vids = None
        if not vids:
            continue
        v = vids.filtered(lambda x: getattr(x, 'active', True))[:1]
        if not v:
            continue
        v = v[0]
        # Thumbnail priority: local upload → bunny auto → product image
        thumb = ''
        try:
            if getattr(v, 'thumbnail', False):
                thumb = (f'/web/image/product.video/{v.id}/thumbnail'
                         f'?unique={v.write_date}')
            elif getattr(v, 'bunny_thumb_auto', False) and getattr(v, 'bunny_thumb_url', ''):
                thumb = v.bunny_thumb_url
            else:
                thumb = (f'/web/image/product.template/{p.id}/image_512'
                         f'?unique={p.write_date}')
        except Exception:
            pass
        items.append({
            'product_id': p.id,
            'product_name': p.name,
            'thumbnail': thumb,
        })
        if len(items) >= limit:
            break
    return {'items': items}


RESOLVERS = {
    'cats-grid':       resolve_categories,
    'cats-strip':      resolve_categories,
    'products':        resolve_products,
    'flash':           resolve_products,
    'bestsellers':     resolve_products,
    'rec-ai':          resolve_products,
    'recent':          resolve_products,
    'grid':            resolve_products,
    'vendors':         resolve_vendors,
    'vendor-feat':     resolve_vendors,
    'hero':            resolve_hero,
    'carousel':        resolve_hero,
    'banner-1':        resolve_hero,
    'banner-2':        resolve_hero,
    'banner-3':        resolve_hero,
    # v2.0.34 new block kinds
    'welcome-deal':    resolve_welcome_deal,
    'discount-strip':  resolve_products,
    'mini-cats':       resolve_mini_cats,
    'quick-pills':     resolve_quick_pills,
    'promo-pills':     resolve_quick_pills,
    'pill-filter':     resolve_quick_pills,
    'themed-promo':    resolve_quick_pills,
    # v2.0.36 — Explore More infinite-load grid
    'explore-more':    resolve_explore_more,
    # v2.0.38 — Slider + 5 designs
    'slider':          resolve_slider,
    'tab-nav':         resolve_passthrough,
    'story-bubbles':   resolve_passthrough,
    'lookbook':        resolve_passthrough,
    'sticky-cta':      resolve_passthrough,
    'image-banner':    resolve_passthrough,
    'reels-strip':     resolve_reels_strip,
    'occasion-header': resolve_passthrough,
    'new-user':        resolve_products,
    'trust-strip':     resolve_passthrough,
    # v2.1.75 — 5 promo-section presets (all fetch products by source).
    'promo-spotlight': resolve_products,
    'promo-category':  resolve_products,
    'promo-rank':      resolve_products,
    'promo-arrivals':  resolve_products,
    'promo-mega':      resolve_products,
}


def resolve_block(env, block, lang):
    """Return a copy of `block` with a `data` key embedded, if applicable."""
    kind = block.get('kind')
    fn = RESOLVERS.get(kind)
    if not fn:
        return block
    try:
        data = fn(env, block.get('props') or {}, lang, block=block) or {}
    except Exception as e:
        _logger.warning('Block resolver %s failed: %s', kind, e)
        data = {}
    out = dict(block)
    out['data'] = data
    return out
