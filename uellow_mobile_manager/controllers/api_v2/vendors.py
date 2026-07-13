"""Vendor (multi-vendor) endpoints — /api/mobile/v2/vendors/*"""
from odoo import fields, http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, get_lang, paginate,
    img_url, bilingual, require_auth, current_partner,
)


def _is_following(vendor_id, partner):
    if not partner:
        return False
    Follower = request.env.get('uellow.vendor.follower')
    if Follower is None:
        return False
    return bool(Follower.sudo().search_count([
        ('vendor_id', '=', vendor_id), ('partner_id', '=', partner.id)]))
from .products import serialize_product_card, _domain_published_for_app


def serialize_vendor_card(vendor, lang='en_US'):
    if not vendor:
        return None
    return {
        'id': vendor.id,
        'name': {
            'en': vendor.store_name_en or vendor.display_name or '',
            'ar': vendor.store_name_ar or vendor.store_name_en or vendor.display_name or '',
        },
        'slug': vendor.store_slug or f'v-{vendor.id}',
        'tagline': {
            'en': vendor.store_tagline_en or '',
            'ar': vendor.store_tagline_ar or vendor.store_tagline_en or '',
        },
        'logo':   img_url('uellow.vendor', vendor.id, 'logo_image',
                          unique=vendor.write_date) if 'logo_image' in vendor._fields else None,
        'banner': img_url('uellow.vendor', vendor.id, 'banner_image',
                          unique=vendor.write_date) if 'banner_image' in vendor._fields else None,
        'brand_color': vendor.brand_color or '#F5C320',
        'tier':        vendor.tier or 'standard',
        'country':     vendor.country_id.code if vendor.country_id else None,
        'product_count': _vendor_product_count(vendor),
        'order_count':   int(vendor.order_count or 0),
        'rating':        _vendor_rating(vendor),
    }


def _vendor_product_count(vendor):
    try:
        return request.env['product.template'].sudo().search_count([
            ('vendor_id', '=', vendor.id), ('is_published', '=', True),
        ])
    except Exception:
        return 0


def _vendor_rating(vendor):
    """Average rating across all the vendor's products. Cached briefly
    in a session field so we don't recompute on every list call."""
    try:
        recs = request.env['product.template'].sudo().search(
            [('vendor_id', '=', vendor.id), ('is_published', '=', True)],
            limit=200,
        )
        if not recs:
            return {'avg': 0, 'count': 0}
        totals = [(p.rating_avg or 0, p.rating_count or 0)
                  for p in recs if (p.rating_count or 0) > 0]
        if not totals:
            return {'avg': 0, 'count': 0}
        n = sum(c for _, c in totals)
        s = sum(a * c for a, c in totals)
        return {'avg': round(s / max(n, 1), 1), 'count': n}
    except Exception:
        return {'avg': 0, 'count': 0}


class MobileVendorsAPI(http.Controller):

    @http.route('/api/mobile/v2/vendors', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_vendors(self, **kw):
        lang = get_lang()
        p = get_payload()
        Vendor = request.env.get('uellow.vendor')
        if Vendor is None:
            return ok([])
        domain = []
        if 'state' in Vendor._fields:
            domain.append(('state', 'in', ['approved', 'active']))
        q = (p.get('q') or '').strip()
        if q:
            domain += ['|', ('store_name_en', 'ilike', q),
                            ('store_name_ar', 'ilike', q)]
        recs = Vendor.sudo().search(domain, order='order_count desc, id desc')
        items, meta = paginate(
            recs, page=p.get('page', 1), per_page=p.get('per_page', 24),
            serializer=lambda v: serialize_vendor_card(v, lang),
        )
        return ok(items, meta)

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def vendor_detail(self, vendor_id, **kw):
        lang = get_lang()
        Vendor = request.env.get('uellow.vendor')
        if Vendor is None:
            return fail('UNAVAILABLE', 'Vendor module not installed', 503)
        vendor = Vendor.sudo().browse(vendor_id)
        if not vendor.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        card = serialize_vendor_card(vendor, lang)
        about = {
            'en': getattr(vendor, 'store_about_en', '') or '',
            'ar': getattr(vendor, 'store_about_ar', '') or '',
        }
        return ok({
            **card,
            'about':       about,
            'sla_hours':   vendor.sla_hours or 0,
            'phone':       vendor.contact_phone or '',
            'business_name': vendor.business_name or '',
            'categories':  _vendor_category_breakdown(vendor),
            'is_following': _is_following(vendor.id, current_partner()),
            'follower_count': int(getattr(vendor, 'follower_count', 0) or 0),
        })

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>/follow',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def vendor_follow(self, vendor_id, **kw):
        """v2.2.34 — toggle following a vendor for the logged-in customer.
        Body {follow: true/false}; omitted → toggle. Persists server-side in
        uellow.vendor.follower (the website store page reads the same model)."""
        partner = current_partner()
        Vendor = request.env.get('uellow.vendor')
        Follower = request.env.get('uellow.vendor.follower')
        if Vendor is None or Follower is None:
            return fail('UNAVAILABLE', 'Vendor module not installed', 503)
        vendor = Vendor.sudo().browse(vendor_id)
        if not vendor.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        p = get_payload()
        existing = Follower.sudo().search([
            ('vendor_id', '=', vendor_id), ('partner_id', '=', partner.id)], limit=1)
        want = p.get('follow')
        if want is None:
            want = not existing  # toggle
        want = bool(want) if not isinstance(want, str) else want.lower() in ('1', 'true', 'yes')
        if want and not existing:
            Follower.sudo().create({'vendor_id': vendor_id, 'partner_id': partner.id})
        elif not want and existing:
            existing.unlink()
        return ok({'following': want,
                   'follower_count': int(getattr(vendor, 'follower_count', 0) or 0)})

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>/storefront',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def vendor_storefront(self, vendor_id, **kw):
        """v2.1.66 — everything the redesigned vendor page needs in ONE
        call: hero/info, flash sale, new arrivals, best sellers,
        category rails, offers (flash + joined campaigns), reviews."""
        lang = get_lang()
        Vendor = request.env.get('uellow.vendor')
        if Vendor is None:
            return fail('UNAVAILABLE', 'Vendor module not installed', 503)
        vendor = Vendor.sudo().browse(vendor_id)
        if not vendor.exists():
            return fail('NOT_FOUND', 'Vendor not found', 404)
        Tmpl = request.env['product.template'].sudo()
        base_dom = _domain_published_for_app() + [('vendor_id', '=', vendor_id)]

        def cards(recs):
            out = []
            for r in recs:
                try:
                    out.append(serialize_product_card(r, lang))
                except Exception:
                    continue
            return out

        # One catalog scan; best-sellers ranked by REAL sold quantity
        # (sale.report aggregate — product.template.sales_count is a
        # non-stored compute and cannot be used as a search order).
        all_prods = Tmpl.search(base_dom, order='create_date desc',
                                limit=400)
        rank = {}
        try:
            for g in request.env['sale.report'].sudo().read_group(
                    [('product_tmpl_id', 'in', all_prods.ids),
                     ('state', 'in', ('sale', 'done'))],
                    ['product_uom_qty'], ['product_tmpl_id']):
                tid = (g.get('product_tmpl_id') or (0,))[0]
                rank[tid] = float(g.get('product_uom_qty') or 0)
        except Exception:
            rank = {}

        def by_rank(recs):
            return sorted(recs, key=lambda p: -rank.get(p.id, 0))

        new_arrivals = cards(all_prods[:10])
        best_sellers = cards(by_rank(all_prods)[:10])

        # ── flash sale (this vendor's active campaign) ────────────────
        flash = None
        offers = []
        FS = request.env.get('uellow.flash.sale')
        if FS is not None:
            try:
                now = fields.Datetime.now()
                for f in FS.sudo().search([
                        ('vendor_id', '=', vendor_id),
                        ('state', '=', 'active'),
                        ('end_datetime', '>', now)], limit=3):
                    fp = f.product_ids.filtered(
                        lambda p: p.active and p.is_published)
                    entry = {
                        'name': {'en': f.name or '',
                                 'ar': getattr(f, 'name_ar', '') or f.name or ''},
                        'discount_pct': float(f.discount_pct or 0),
                        'ends_at': f.end_datetime.isoformat()
                                   if f.end_datetime else None,
                        'products': cards(fp[:10]),
                    }
                    if flash is None and entry['products']:
                        flash = entry
                    offers.append({
                        'type': 'flash', 'emoji': '⚡',
                        'label': entry['name'],
                        'discount_pct': entry['discount_pct'],
                        'date_to': entry['ends_at'],
                    })
            except Exception:
                pass

        # ── joined marketplace campaigns (approved lines) ─────────────
        try:
            Line = request.env.get('mobile.promotion.line')
            if Line is not None:
                seen_promos = set()
                for l in Line.sudo().search([
                        ('vendor_id', '=', vendor_id),
                        ('state', '=', 'approved')], limit=50):
                    pr = l.promotion_id
                    if not pr or pr.id in seen_promos or \
                            pr.state not in ('open', 'running'):
                        continue
                    seen_promos.add(pr.id)
                    offers.append({
                        'type': 'campaign',
                        'emoji': pr.emoji or '🎉',
                        'label': {'en': pr.label_en or '',
                                  'ar': pr.label_ar or pr.label_en or ''},
                        'discount_pct': float(l.discount_pct or 0),
                        'date_to': pr.date_to.isoformat()
                                   if pr.date_to else None,
                    })
        except Exception:
            pass

        # ── category rails (direct category match, best sellers first) ─
        cats = _vendor_category_breakdown(vendor)
        rails = []
        for c in cats[:6]:
            prods = by_rank(all_prods.filtered(
                lambda p: c['id'] in p.public_categ_ids.ids))[:10]
            if prods:
                rails.append({'category': c, 'products': cards(prods)})

        # ── recent reviews on this vendor's products ──────────────────
        reviews = []
        try:
            pids = all_prods.ids
            if pids:
                Rating = request.env['rating.rating'].sudo()
                for r in Rating.search([
                        ('res_model', '=', 'product.template'),
                        ('res_id', 'in', pids),
                        ('consumed', '=', True),
                        ('rating', '>', 0)],
                        order='create_date desc', limit=10):
                    prod = Tmpl.browse(r.res_id)
                    reviews.append({
                        'stars': round(float(r.rating or 0), 1),
                        'title': getattr(r, 'review_title', '') or '',
                        'text': r.feedback or '',
                        'customer': (r.partner_id.name or '').split(' ')[0]
                                    if r.partner_id else '',
                        'verified': bool(getattr(
                            r, 'is_verified_purchase', False)),
                        'date': r.create_date.isoformat()
                                if r.create_date else None,
                        'product': {
                            'id': prod.id,
                            'name': bilingual(prod, 'name'),
                            'image': img_url('product.template', prod.id,
                                             'image_256',
                                             unique=prod.write_date),
                        } if prod.exists() else None,
                    })
        except Exception:
            pass

        card = serialize_vendor_card(vendor, lang)
        return ok({
            'vendor': {
                **card,
                'about': {
                    'en': getattr(vendor, 'store_about_en', '') or
                          getattr(vendor, 'store_description_en', '') or '',
                    'ar': getattr(vendor, 'store_about_ar', '') or
                          getattr(vendor, 'store_description_ar', '') or '',
                },
                'sla_hours': vendor.sla_hours or 0,
            },
            'flash_sale': flash,
            'new_arrivals': new_arrivals,
            'best_sellers': best_sellers,
            'categories': cats,
            'category_rails': rails,
            'offers': offers,
            'reviews': {'summary': card.get('rating') or
                        {'avg': 0, 'count': 0},
                        'items': reviews},
        })

    @http.route('/api/mobile/v2/vendors/<int:vendor_id>/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def vendor_products(self, vendor_id, **kw):
        lang = get_lang()
        p = get_payload()
        domain = _domain_published_for_app() + [('vendor_id', '=', vendor_id)]
        sort = {
            'newest':     'create_date desc',
            'price_asc':  'list_price asc',
            'price_desc': 'list_price desc',
            'top_rated':  'rating_avg desc' if 'rating_avg' in request.env['product.template']._fields else 'create_date desc',
        }.get(p.get('sort', 'newest'), 'create_date desc')
        # perf — page at SQL level instead of fetching the vendor's whole catalog
        Tmpl = request.env['product.template'].sudo()
        try:
            _page = max(1, int(p.get('page', 1)))
        except Exception:
            _page = 1
        try:
            _per = min(100, max(1, int(p.get('per_page', 20))))
        except Exception:
            _per = 20
        _total = Tmpl.search_count(domain)
        recs = Tmpl.search(domain, order=sort, limit=_per, offset=(_page - 1) * _per)
        items = [serialize_product_card(r, lang) for r in recs]
        meta = {'page': _page, 'per_page': _per, 'total': _total,
                'pages': (_total + _per - 1) // _per,
                'has_next': _page * _per < _total}
        return ok(items, meta)


def _vendor_category_breakdown(vendor):
    """Top public categories this vendor sells in — useful for the
    vendor page's mini-nav."""
    recs = request.env['product.template'].sudo().search(
        [('vendor_id', '=', vendor.id), ('is_published', '=', True)],
        limit=300,
    )
    counts = {}
    for p in recs:
        for c in p.public_categ_ids:
            counts[c.id] = counts.get(c.id, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    cats = request.env['product.public.category'].sudo().browse([cid for cid, _ in top])
    by_id = {c.id: c for c in cats}
    return [{
        'id': cid,
        'name': bilingual(by_id[cid], 'name'),
        'count': cnt,
    } for cid, cnt in top if cid in by_id]
