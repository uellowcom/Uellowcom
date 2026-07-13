# -*- coding: utf-8 -*-
"""Storefront + mobile-app access to the dropship catalog.

Browsing reads the lightweight ``dropship.product`` table (no product.template
yet). Only when a customer opens a product to buy do we materialize a real
product on the isolated Uellow website and redirect to the SAME Uellow product
page template — so the page looks identical to the rest of the store.
"""
import logging

from datetime import date
from urllib.parse import quote

from odoo import http
from odoo.http import request

# Same HD upgrade the app/reels use: AliExpress's templated player URL streams
# SD; the canonical /play/<id>.mp4 form yields the HD master when it exists.
from .app_bridge import _hd_video_url

_logger = logging.getLogger(__name__)


class DropshipStorefront(http.Controller):

    # ---- mobile app / JSON feed -------------------------------------- #
    @http.route('/dropship/feed', type='json', auth='public', methods=['POST'], csrf=False)
    def feed(self, page=1, page_size=None, category=None, search=None, deals_only=False, **kw):
        """Paginated listing feed for the app / storefront rails."""
        ICP = request.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return {'enabled': False, 'items': [], 'total': 0}

        page = max(int(page or 1), 1)
        page_size = int(page_size or ICP.get_param('uellow_dropship.products_per_page', 40) or 40)
        domain = []
        if category:
            domain.append(('category', '=', str(category)))
        if search:
            domain += ['|', ('title_en', 'ilike', search), ('title_ar', 'ilike', search)]
        if deals_only in (True, 'true', '1', 1):
            domain.append(('is_deal', '=', True))

        # eligibility gate: min landed price
        min_price = float(ICP.get_param('uellow_dropship.min_price', 0.0) or 0.0)
        if min_price:
            domain.append(('sale_price', '>=', min_price))

        Product = request.env['dropship.product'].sudo()
        order = self._order(ICP.get_param('uellow_dropship.sort_default', 'orders'))
        total = Product.search_count(domain)
        recs = Product.search(domain, order=order,
                              limit=page_size, offset=(page - 1) * page_size)
        return {
            'enabled': True,
            'brand': ICP.get_param('uellow_dropship.brand_name', 'Uellow World'),
            'page': page, 'page_size': page_size, 'total': total,
            'items': [self._card(r, ICP) for r in recs],
        }

    def _order(self, sort):
        return {
            'deal': 'discount_percent desc, id desc',
            'new': 'id desc',
            'price_asc': 'sale_price asc',
            'orders': 'id desc',
        }.get(sort, 'id desc')

    def _card(self, rec, ICP):
        show_video = ICP.get_param('uellow_dropship.show_videos') in ('True', '1', 'true')
        lang_ar = ICP.get_param('uellow_dropship.default_lang') == 'ar'
        title = (rec.title_ar or rec.title_en) if lang_ar else (rec.title_en or rec.title_ar)
        return {
            'id': rec.id,
            'title': title,
            'title_en': rec.title_en,
            'title_ar': rec.title_ar,
            'price': round(rec.sale_price, 3),
            'original_price': round(rec.original_price, 3) if rec.original_price else None,
            'discount_percent': rec.discount_percent or None,
            'is_deal': rec.is_deal,
            'image': rec.image_url,
            'video': _hd_video_url(rec.video_url) if show_video else None,
            'url': '/dropship/p/%s' % rec.id,
        }

    # country grid entry (mirrors the app entry: countries + China Hub) ---- #
    COUNTRIES = [
        {'flag': '🇨🇳', 'name': 'China', 'name_ar': 'الصين', 'code': 'CN', 'featured': True},
        {'flag': '🇦🇪', 'name': 'UAE', 'name_ar': 'الإمارات', 'code': 'AE'},
        {'flag': '🇸🇦', 'name': 'Saudi Arabia', 'name_ar': 'السعودية', 'code': 'SA'},
        {'flag': '🇰🇼', 'name': 'Kuwait', 'name_ar': 'الكويت', 'code': 'KW'},
        {'flag': '🇶🇦', 'name': 'Qatar', 'name_ar': 'قطر', 'code': 'QA'},
        {'flag': '🇴🇲', 'name': 'Oman', 'name_ar': 'عُمان', 'code': 'OM'},
        {'flag': '🇹🇷', 'name': 'Türkiye', 'name_ar': 'تركيا', 'code': 'TR'},
        {'flag': '🇺🇸', 'name': 'USA', 'name_ar': 'أمريكا', 'code': 'US'},
    ]

    def _world_categories(self, deals=None, limit=14):
        """Build category tiles from the SEPARATE, module-only dropship.category
        records (each carries a bilingual name + emoji icon). Counts come from the
        lightweight catalog. Shared by the entry page and the shop.
        """
        Product = request.env['dropship.product'].sudo()
        base_domain = [('is_deal', '=', True)] if deals else []
        groups = Product.read_group(base_domain + [('category_name', '!=', False)],
                                    ['category_name'], ['category_name'])
        counts = {g['category_name']: (g.get('__count') or g.get('category_name_count') or 0)
                  for g in groups if g.get('category_name')}
        categories = []
        for dc in request.env['dropship.category'].sudo().search([]):
            cnt = counts.get(dc.code)
            if not cnt:  # only show categories that actually have products
                continue
            categories.append({
                'name': dc.code,          # provider name = filter key (stable, lang-neutral)
                'label': dc.name,         # display name (translatable EN + AR)
                'icon': dc.icon or '🏷️',
                'count': cnt,
                'url': '/world/shop?category=%s%s' % (
                    quote(dc.code), '&deals=1' if deals else ''),
            })
        categories.sort(key=lambda x: x['count'], reverse=True)
        return categories[:limit] if limit else categories

    @http.route('/world', type='http', auth='public', website=True, sitemap=True)
    def world_entry(self, **kw):
        ICP = request.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return request.not_found()
        total = request.env['dropship.product'].sudo().search_count([])
        return request.render('uellow_dropship.world_entry', {
            'countries': self.COUNTRIES,
            'categories': self._world_categories(limit=18),
            'total': total,
            'brand': ICP.get_param('uellow_dropship.brand_name', 'Uellow World'),
        })

    # storefront sort options -> ORM order clause
    _SORTS = {
        'featured': 'is_deal desc, discount_percent desc, id desc',
        'price_asc': 'sale_price asc, id desc',
        'price_desc': 'sale_price desc, id desc',
        'discount': 'discount_percent desc, id desc',
        'newest': 'id desc',
    }

    # ---- website browsing page (Uellow World storefront) ------------- #
    @http.route(['/world/shop', '/world/shop/page/<int:page>'], type='http',
                auth='public', website=True, sitemap=False)
    def world_shop(self, page=1, search=None, deals=None, country=None, category=None,
                   sort=None, **kw):
        ICP = request.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return request.not_found()

        Product = request.env['dropship.product'].sudo()
        domain = []
        if search:
            domain += ['|', ('title_en', 'ilike', search), ('title_ar', 'ilike', search)]
        if deals:
            domain.append(('is_deal', '=', True))
        if category:
            domain.append(('category_name', '=', category))
        min_price = float(ICP.get_param('uellow_dropship.min_price', 0.0) or 0.0)
        if min_price:
            domain.append(('sale_price', '>=', min_price))

        categories = self._world_categories(deals=deals, limit=14)

        sort = sort if sort in self._SORTS else 'featured'
        page_size = int(ICP.get_param('uellow_dropship.products_per_page', 40) or 40)
        total = Product.search_count(domain)
        pager = request.website.pager(
            url='/world/shop', total=total, page=page, step=page_size,
            url_args={'search': search, 'deals': deals, 'country': country,
                      'category': category, 'sort': sort})
        recs = Product.search(domain, limit=page_size, offset=pager['offset'],
                              order=self._SORTS[sort])
        # Geo display currency: default USD, switches to the visitor's own
        # currency (Cloudflare CF-IPCountry / GeoIP) — same rule as the app. The
        # dropship sale_price is stored in the company currency (KWD); we convert
        # it for DISPLAY only (checkout on the standard product page is unchanged).
        currency, prices = self._world_prices(recs)
        return request.render('uellow_dropship.world_shop', {
            'products': recs,
            'pager': pager,
            'search': search or '',
            'deals': deals,
            'category': category or '',
            'categories': categories,
            'sort': sort,
            'total': total,
            'currency': currency,
            'prices': prices,
            'brand': ICP.get_param('uellow_dropship.brand_name', 'Uellow World'),
        })

    def _world_prices(self, recs):
        """(display_currency, {ds_id: {'now': txt, 'was': txt|None}}) — convert
        each product's company-currency sale_price to the visitor's geo currency
        (default USD) for display. Reuses the app's geo-currency resolver."""
        from .app_bridge import _world_currency
        disp = _world_currency()
        # Rate context MUST be the company that owns the FX rate table (the main
        # company, id 1). A website=True request runs under the World company
        # (id 7, KWD) which has NO rate rows, so Odoo would silently assume 1:1
        # and skip conversion — that's why the app (public API, runs under the
        # main company) converts correctly but /world/shop did not.
        rate_company = request.env['res.company'].sudo().search(
            [], order='id asc', limit=1)
        src = rate_company.currency_id
        today = date.today()

        def _conv(v):
            v = float(v or 0.0)
            if disp and src and disp.id != src.id:
                try:
                    return src._convert(v, disp, rate_company, today)
                except Exception:  # noqa: BLE001
                    return v
            return v

        digits = disp.decimal_places if disp else 2
        out = {}
        for p in recs:
            now = _conv(p.sale_price)
            was = (_conv(p.original_price)
                   if (p.original_price and p.original_price > p.sale_price)
                   else None)
            out[p.id] = {
                'now': '%.*f' % (digits, now),
                'was': ('%.*f' % (max(digits - 1, 0), was)) if was else None,
            }
        return disp, out

    # ---- open a product: materialize + go to the Uellow product page --- #
    @http.route('/dropship/p/<int:ds_id>', type='http', auth='public', website=True, sitemap=False)
    def open_product(self, ds_id, **kw):
        rec = request.env['dropship.product'].sudo().browse(ds_id).exists()
        if not rec:
            return request.not_found()
        # lazy enrichment: fetch the full description + specs + shipping +
        # review summary once (freshness-guarded, fail-soft) BEFORE materialize
        # so the created product page carries the complete provider content.
        try:
            rec._enrich_detail()
        except Exception as e:  # noqa: BLE001 - never block opening a product
            _logger.info("enrich failed for %s: %s", ds_id, e)
        # lazy materialization: create the real product only now
        tmpl = rec._materialize()
        # a customer opened it on purpose -> make sure the page is visible
        if not tmpl.website_published:
            tmpl.sudo().website_published = True
        request.env.cr.commit()  # persist the new product from this request
        # redirect to the standard Uellow product page (same template as the store)
        try:
            slug = request.env['ir.http']._slug(tmpl)
        except Exception:  # noqa: BLE001 - slug helper name varies; id is always accepted
            slug = tmpl.id
        return request.redirect('/shop/%s' % slug)

    # ---- video proxy: hide the provider CDN behind a Uellow URL -------- #
    @http.route('/dropship/video/<int:tmpl_id>', type='http', auth='public',
                website=True, sitemap=False)
    def dropship_video(self, tmpl_id, **kw):
        """Serve a dropship product's video from a Uellow URL (no provider CDN).

        Cached as an ir.attachment on first view (bounded to materialized
        products), then served by /web/content — so no worker re-streams it and
        the customer never sees an 'aliexpress' URL. Fail-soft: falls back to the
        raw source URL only if the one-time cache fetch fails.
        """
        tmpl = request.env['product.template'].sudo().browse(tmpl_id).exists()
        if not tmpl or not tmpl.is_dropship:
            return request.not_found()
        ds = tmpl.dropship_product_id
        src = _hd_video_url(ds and ds.video_url)
        if not src:
            return request.not_found()
        Att = request.env['ir.attachment'].sudo()
        name = 'ds_video_%s.mp4' % tmpl_id
        cached = Att.search([('res_model', '=', 'product.template'),
                             ('res_id', '=', tmpl_id), ('name', '=', name)], limit=1)
        if not cached:
            try:
                import requests
                if src.startswith('//'):
                    src = 'https:' + src
                resp = requests.get(src, timeout=25, stream=True, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; UellowBot/1.0)'})
                content = resp.content if resp.status_code == 200 else b''
                # cap storage: skip caching very large files (still fall back below)
                if content and len(content) <= 40 * 1024 * 1024:
                    cached = Att.create({
                        'name': name,
                        'res_model': 'product.template',
                        'res_id': tmpl_id,
                        'mimetype': 'video/mp4',
                        'public': True,
                        'raw': content,
                    })
                    request.env.cr.commit()
            except Exception as e:  # noqa: BLE001 - never hard-fail a video
                _logger.info("dropship video cache failed for %s: %s", tmpl_id, e)
        if cached:
            return request.redirect('/web/content/%s' % cached.id, code=302)
        # last resort: stream the source URL directly (rare)
        return request.redirect(src, code=302)

    # ---- image proxy: hide the provider CDN behind a Uellow URL ------- #
    # Host allow-list for the one-time server-side fetch. image_url comes from the
    # provider adapter (not user input), but we still restrict the fetch target.
    _IMG_HOST_OK = (
        'aliexpress-media.com', 'alicdn.com', 'aliexpress.com',
        'ae01.alicdn.com', 'ae-pic', 'kwcdn.com', 'cjdropshipping',
    )

    @http.route('/dropship/media', type='http', auth='public',
                website=True, sitemap=False)
    def dropship_media(self, u=None, **kw):
        """Proxy an arbitrary provider-CDN image behind a Uellow URL.

        Used to rewrite the images embedded INSIDE the product description HTML
        (the AliExpress ``detail`` blob is full of ``ae01.alicdn.com`` <img>s):
        serving them through here keeps the page free of any provider-CDN link
        and immune to hot-link rate-limiting. Host allow-listed (SSRF guard),
        cached once as a public ir.attachment keyed by the URL hash, then served
        by /web/content. Fail-soft: 302 to the raw URL if the fetch fails.
        """
        if not u:
            return request.not_found()
        # `u` is base64(url) (current) or a percent-encoded URL (legacy) — try
        # base64 first, fall back to plain unquote.
        import base64
        from urllib.parse import unquote
        src = ''
        try:
            decoded = base64.urlsafe_b64decode(u.encode('ascii')).decode('utf-8')
            if '://' in decoded or decoded.startswith('//'):
                src = decoded
        except Exception:  # noqa: BLE001
            src = ''
        if not src:
            src = unquote(u)
        if src.startswith('//'):
            src = 'https:' + src
        if not any(h in src for h in self._IMG_HOST_OK):
            return request.not_found()
        import hashlib
        key = hashlib.sha1(src.encode('utf-8')).hexdigest()
        name = 'ds_media_%s' % key
        Att = request.env['ir.attachment'].sudo()
        cached = Att.search([('res_model', '=', 'dropship.product'),
                             ('name', '=', name)], limit=1)
        if not cached:
            try:
                import requests
                resp = requests.get(src, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; UellowBot/1.0)'})
                content = resp.content if resp.status_code == 200 else b''
                mimetype = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
                if (content and mimetype.startswith('image/')
                        and len(content) <= 8 * 1024 * 1024):
                    cached = Att.create({
                        'name': name,
                        'res_model': 'dropship.product',
                        'res_id': 0,
                        'mimetype': mimetype,
                        'public': True,
                        'raw': content,
                    })
                    request.env.cr.commit()
            except Exception as e:  # noqa: BLE001 - never hard-fail a description image
                _logger.info("dropship media cache failed for %s: %s", src, e)
        if cached:
            return request.redirect('/web/content/%s' % cached.id, code=302)
        return request.redirect(src, code=302)

    @http.route('/dropship/img/<int:ds_id>', type='http', auth='public',
                website=True, sitemap=False)
    def dropship_img(self, ds_id, **kw):
        """Serve a dropship product's listing image from a Uellow URL, so neither
        the storefront nor the app ever exposes an 'aliexpress' CDN link, and the
        image keeps working if the provider CDN rate-limits hot-linking.

        Cached once as a public ir.attachment on the dropship.product record, then
        served by /web/content. Fail-soft: redirect to the raw source URL if the
        one-time fetch fails or the host is not an allowed provider CDN.
        """
        rec = request.env['dropship.product'].sudo().browse(ds_id).exists()
        src = rec and (rec.image_url or '')
        if not src:
            return request.not_found()
        if src.startswith('//'):
            src = 'https:' + src
        Att = request.env['ir.attachment'].sudo()
        name = 'ds_img_%s' % ds_id
        cached = Att.search([('res_model', '=', 'dropship.product'),
                             ('res_id', '=', ds_id), ('name', '=', name)], limit=1)
        if not cached and any(h in src for h in self._IMG_HOST_OK):
            try:
                import requests
                resp = requests.get(src, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; UellowBot/1.0)'})
                content = resp.content if resp.status_code == 200 else b''
                mimetype = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
                # only cache real images, capped so filestore can't balloon
                if (content and mimetype.startswith('image/')
                        and len(content) <= 8 * 1024 * 1024):
                    cached = Att.create({
                        'name': name,
                        'res_model': 'dropship.product',
                        'res_id': ds_id,
                        'mimetype': mimetype,
                        'public': True,
                        'raw': content,
                    })
                    request.env.cr.commit()
            except Exception as e:  # noqa: BLE001 - never hard-fail an image
                _logger.info("dropship img cache failed for %s: %s", ds_id, e)
        if cached:
            return request.redirect('/web/content/%s' % cached.id, code=302)
        # last resort: hot-link the source (rare — bad host or fetch error)
        return request.redirect(src, code=302)
