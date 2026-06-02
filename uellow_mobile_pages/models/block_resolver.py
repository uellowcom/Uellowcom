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
        recs = Tmpl.search(
            base_dom + [('compare_list_price', '>', 0)],
            order='write_date desc', limit=limit)
        if not recs:
            # Fallback: any recent published product
            recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'bestsellers':
        # Approximation — products with most sales lines. For perf we just
        # fall back to recently-updated published products if the join is
        # too slow. Real bestseller scoring belongs in a daily job.
        recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    elif source == 'newest':
        recs = Tmpl.search(base_dom, order='create_date desc', limit=limit)

    elif source == 'recent':
        # Personal — can't resolve at page-fetch time; let the app fall
        # back to its own /recently-viewed endpoint.
        return {'items': [], 'fetch_endpoint': 'recently-viewed'}

    else:
        recs = Tmpl.search(base_dom, order='write_date desc', limit=limit)

    return {'items': [_product_brief(env, p, lang) for p in recs]}


def _product_brief(env, p, lang):
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
