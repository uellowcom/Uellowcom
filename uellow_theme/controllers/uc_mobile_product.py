# -*- coding: utf-8 -*-
"""App-faithful mobile product page.

Served two ways:
  * /m/p/<id>                         -> always (direct / preview / QA)
  * /shop/<slug>  on a PHONE          -> same URL, app UI (SEO-safe dynamic
                                         serving with Vary: User-Agent)

SSR strategy for SEO + extreme speed:
  * the full product object (same serializer the app's API uses) is embedded
    inline as window.__P__  -> the JS renders every block instantly, no fetch.
  * <head> carries full meta + Open Graph + Twitter + JSON-LD Product schema.
  * a real server-rendered critical block (h1 / price / image / description)
    ships in the body so crawlers and first paint get real content.

Kill switch: ir.config_parameter `uellow.m_product_enabled` = '0' disables the
/shop takeover instantly (the /m/p/<id> route always keeps working).
User escape: /shop/<slug>?full=1 (or cookie m_full=1) forces the desktop page.
"""
import json
import os
import re

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

try:
    from odoo.addons.uellow_mobile_manager.controllers.api_v2.products import (
        serialize_product_full,
    )
except Exception:  # pragma: no cover
    serialize_product_full = None

_HTML = {}
_PHONE_RE = re.compile(r'(iphone|ipod|android.*mobile|windows phone|mobi)', re.I)


def _load_html(sub="m"):
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "static", "src", sub, "product.html"))
    st = os.stat(path)
    c = _HTML.get(sub)
    if not c or c["mtime"] != st.st_mtime:
        with open(path, "r", encoding="utf-8") as f:
            _HTML[sub] = {"src": f.read(), "mtime": st.st_mtime}
    return _HTML[sub]["src"]


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _loc(v, lang):
    if isinstance(v, dict):
        if lang and lang.startswith("ar"):
            return v.get("ar") or v.get("en") or v.get("value") or ""
        return v.get("en") or v.get("ar") or v.get("value") or ""
    return v or ""


def _plain(html, limit=300):
    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


def _money(v):
    try:
        n = round(float(v or 0), 3)
    except Exception:
        n = 0
    s = ("%.3f" % n).rstrip('0').rstrip('.')
    return s or '0'


def _is_phone():
    ua = request.httprequest.headers.get('User-Agent') or ''
    return bool(_PHONE_RE.search(ua))


def _takeover_enabled():
    val = request.env['ir.config_parameter'].sudo().get_param(
        'uellow.m_product_enabled', '1')
    return str(val) not in ('0', 'false', 'False', '')


def render_app_product(tmpl, noindex=False, template="m"):
    """Build the full app-style page response for a product.template record."""
    lang = (request.env.context.get('lang') or 'ar_001')
    base = request.httprequest.host_url.rstrip('/')
    html = _load_html(template)

    if not (tmpl and tmpl.exists() and tmpl.is_published and serialize_product_full):
        page = (html.replace('/*__P__*/null', json.dumps({"_missing": True}))
                    .replace('__PID__', str(tmpl.id if tmpl else 0))
                    .replace('__HEAD__', '<title>يلو · uellow</title>')
                    .replace('__SSR__', ''))
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8')])

    try:
        p = serialize_product_full(tmpl, lang)
    except Exception:
        p = serialize_product_full(tmpl)
    # Localize price to the website pricelist currency (per-country stores).
    try:
        _pl = None
        try:
            _pl = request.website._get_current_pricelist()
        except Exception:
            _pl = request.website.pricelist_id
        if _pl and _pl.currency_id and p.get('price'):
            from odoo import fields as _flds
            _plc = _pl.currency_id
            _amt = _pl._get_product_price(tmpl.product_variant_id, 1.0)
            _sym = _plc.symbol or _plc.name
            p['price'] = {'amount': round(float(_amt), 3), 'symbol': _sym, 'currency': _plc.name}
            _cmp_kwd = float(getattr(tmpl, 'compare_list_price', 0) or 0)
            if _cmp_kwd and _cmp_kwd > float(tmpl.list_price or 0):
                _cmp_loc = tmpl.currency_id._convert(_cmp_kwd, _plc, request.env.company, _flds.Date.today())
                p['compare_price'] = {'amount': round(float(_cmp_loc), 3), 'symbol': _sym, 'currency': _plc.name}
    except Exception:
        pass

    pid = tmpl.id
    try:
        variant_id = tmpl.product_variant_id.id if tmpl.product_variant_id else 0
    except Exception:
        variant_id = 0
    name = _loc(p.get('name'), lang) or (tmpl.name or '')
    price = (p.get('price') or {}).get('amount') or 0
    sym = (p.get('price') or {}).get('symbol') or 'KD'
    cur = (p.get('price') or {}).get('currency') or 'KWD'
    cmp_amt = (p.get('compare_price') or {}).get('amount')
    images = [i for i in (p.get('images') or []) if i]
    img0 = images[0] if images else (p.get('image') or '')
    desc = _plain(_loc(p.get('description_html'), lang)
                  or _loc(p.get('description_short'), lang), 300)
    brand = _loc((p.get('brand') or {}).get('name'), lang)
    rating = p.get('rating') or {}
    in_stock = bool(p.get('in_stock') or p.get('allow_out_of_stock_order'))
    https = base.replace('http://', 'https://')
    canon = https + (tmpl.website_url or '/shop')
    img0s = (img0 or '').replace('http://', 'https://')
    img_disp = re.sub(r'/image_\d+', '/image_1024', img0s) if img0s else img0s
    off = p.get('discount_pct') or 0
    is_ar = bool(lang and lang.startswith('ar'))

    # ── SEO meta: reuse the AI-generated website_meta_* (fallback to derived) ──
    meta_title = (tmpl.website_meta_title or ('%s | uellow يلو' % name)).strip()
    meta_desc = (tmpl.website_meta_description or desc or name).strip()
    meta_kw = (tmpl.website_meta_keywords or '').strip()

    # ── rich Product JSON-LD from seo_auto (offers/availability/rating) ──
    try:
        product_ld = request.env['uellow.seo.product'].sudo()._build_product_jsonld(
            tmpl, tmpl.with_context(lang='en_US'))
    except Exception:
        product_ld = {
            "@context": "https://schema.org", "@type": "Product", "name": name,
            "description": meta_desc, "sku": p.get('sku') or str(pid), "url": canon,
            "offers": {
                "@type": "Offer", "price": "%.3f" % float(price or 0),
                "priceCurrency": cur, "url": canon,
                "availability": "https://schema.org/%s" % (
                    "InStock" if in_stock else "OutOfStock")},
        }
    try:
        imgs = product_ld.get('image')
        imgs = [imgs] if isinstance(imgs, str) else (imgs or images or [img0s])
        product_ld['image'] = [(u or '').replace('http://', 'https://') for u in imgs][:6] or [img0s]
        product_ld.setdefault('url', canon)
        product_ld.setdefault('description', meta_desc)
        _g = request.env['uellow.seo.product'].sudo()._valid_gtin(p.get('barcode'))
        if _g:
            product_ld['gtin%d' % len(_g)] = _g
        if brand and 'brand' not in product_ld:
            product_ld['brand'] = {"@type": "Brand", "name": brand}
        if isinstance(product_ld.get('offers'), dict):
            product_ld['offers'].setdefault('url', canon)
            product_ld['offers']['itemCondition'] = 'https://schema.org/NewCondition'
            product_ld['offers']['seller'] = {"@type": "Organization", "name": "Uellow يلو"}
            try:
                if p.get('price'):
                    product_ld['offers']['price'] = '%.3f' % float(p['price']['amount'])
                    product_ld['offers']['priceCurrency'] = p['price']['currency']
            except Exception:
                pass
            # merchant listing signals (accurate: 14-day free return, KW 1-3 day delivery)
            product_ld['offers']['hasMerchantReturnPolicy'] = {
                "@type": "MerchantReturnPolicy", "applicableCountry": "KW",
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": 14,
                "returnMethod": "https://schema.org/ReturnByMail",
                "returnFees": "https://schema.org/FreeReturn"}
            product_ld['offers']['shippingDetails'] = {
                "@type": "OfferShippingDetails",
                "shippingRate": {"@type": "MonetaryAmount", "value": "0.000",
                                 "currency": (p.get('price') or {}).get('currency') or 'KWD'},
                "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "KW"},
                "deliveryTime": {"@type": "ShippingDeliveryTime",
                    "handlingTime": {"@type": "QuantitativeValue",
                                     "minValue": 0, "maxValue": 1, "unitCode": "DAY"},
                    "transitTime": {"@type": "QuantitativeValue",
                                    "minValue": 1, "maxValue": 3, "unitCode": "DAY"}}}
        if 'aggregateRating' not in product_ld and (rating.get('count') or 0) > 0 \
                and (rating.get('avg') or 0) > 0:
            product_ld['aggregateRating'] = {
                "@type": "AggregateRating",
                "ratingValue": round(float(rating.get('avg')), 1),
                "reviewCount": int(rating.get('count')),
                "bestRating": 5, "worstRating": 1}
    except Exception:
        pass

    # ── BreadcrumbList ──
    cat_name = ''
    crumbs = [{"@type": "ListItem", "position": 1,
               "name": ("المتجر" if is_ar else "Shop"), "item": https + "/shop"}]
    if p.get('categories'):
        cat_name = _loc(p['categories'][0].get('name'), lang)
        if cat_name:
            crumbs.append({"@type": "ListItem", "position": 2,
                           "name": cat_name, "item": https + "/shop"})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1,
                   "name": name, "item": canon})
    breadcrumb_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                     "itemListElement": crumbs}

    # ── Organization + WebSite (SearchAction) ──
    wid = request.website.id if request.website else 1
    org_ld = {"@context": "https://schema.org", "@type": "Organization",
              "name": "Uellow يلو", "url": https + "/",
              "logo": https + "/web/image/website/%s/logo" % wid}
    website_ld = {"@context": "https://schema.org", "@type": "WebSite",
                  "name": "Uellow يلو", "url": https + "/",
                  "potentialAction": {"@type": "SearchAction",
                                      "target": https + "/shop?search={search_term_string}",
                                      "query-input": "required name=search_term_string"}}

    # ── FAQPage (unique per-product FAQs from uellow_seo) — SERP rich result ──
    try:
        faq_ld = tmpl._seo_faq_jsonld()
        if isinstance(faq_ld, str):
            faq_ld = json.loads(faq_ld) if faq_ld.strip() else None
        if faq_ld and not (faq_ld.get('mainEntity') if isinstance(faq_ld, dict) else None):
            faq_ld = None
    except Exception:
        faq_ld = None

    # ── hreflang (reuse the site's reciprocal en/ar country list) ──
    hreflang = ''
    try:
        for hl in (request.website._uellow_country_hreflangs() or []):
            hreflang += '<link rel="alternate" hreflang="%s" href="%s"/>' % (
                _esc(hl.get('hreflang')), _esc(hl.get('href')))
    except Exception:
        hreflang = ''
    if not hreflang:
        hreflang = '<link rel="alternate" hreflang="x-default" href="%s"/>' % _esc(canon)

    robots = 'noindex, follow' if noindex else \
        'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
    _ld = lambda d: '<script type="application/ld+json">%s</script>' % (
        json.dumps(d, ensure_ascii=False).replace('</', '<\\/'))
    parts = [
        '<link rel="preload" as="image" href="%s" fetchpriority="high" imagesizes="100vw"/>' % _esc(img_disp),
        '<title>%s</title>' % _esc(meta_title),
        '<meta name="description" content="%s"/>' % _esc(meta_desc),
        ('<meta name="keywords" content="%s"/>' % _esc(meta_kw)) if meta_kw else '',
        '<meta name="robots" content="%s"/>' % robots,
        '<link rel="canonical" href="%s"/>' % _esc(canon),
        hreflang,
        '<meta property="og:type" content="product"/>',
        '<meta property="og:site_name" content="Uellow يلو"/>',
        '<meta property="og:locale" content="%s"/>' % ('ar_KW' if is_ar else 'en_US'),
        '<meta property="og:title" content="%s"/>' % _esc(meta_title),
        '<meta property="og:description" content="%s"/>' % _esc(meta_desc),
        '<meta property="og:image" content="%s"/>' % _esc(img0s),
        '<meta property="og:image:width" content="1200"/>',
        '<meta property="og:image:height" content="1200"/>',
        '<meta property="og:url" content="%s"/>' % _esc(canon),
        '<meta property="product:price:amount" content="%.3f"/>' % float(price or 0),
        '<meta property="product:price:currency" content="%s"/>' % _esc(cur),
        '<meta property="product:availability" content="%s"/>' % (
            'in stock' if in_stock else 'out of stock'),
        '<meta name="twitter:card" content="summary_large_image"/>',
        '<meta name="twitter:title" content="%s"/>' % _esc(meta_title),
        '<meta name="twitter:description" content="%s"/>' % _esc(meta_desc),
        '<meta name="twitter:image" content="%s"/>' % _esc(img0s),
        _ld(product_ld), _ld(breadcrumb_ld), _ld(org_ld), _ld(website_ld),
        _ld(faq_ld) if faq_ld else '',
    ]
    head = ''.join(parts)

    # ── SSR critical body (real content for crawlers) ──
    price_html = '<span class="ssr-now">%s</span> <span class="ssr-cur">%s</span>' % (
        _esc(_money(price)), _esc(sym))
    if cmp_amt and cmp_amt > price:
        price_html += ' <s class="ssr-was">%s %s</s>' % (_esc(_money(cmp_amt)), _esc(sym))
        if off:
            price_html += ' <span class="ssr-off">-%s%%</span>' % off
    full_desc = _plain(_loc(p.get('description_html'), lang)
                       or _loc(p.get('description_short'), lang), 1500)
    crumb = ['<a href="/shop">%s</a>' % ('المتجر' if is_ar else 'Shop')]
    if cat_name:
        crumb.append(_esc(cat_name))
    crumb.append(_esc(name))
    ssr = (
        '<nav class="ssr-crumb">%s</nav>'
        '<img class="ssr-img" src="%s" alt="%s" width="600" height="600" fetchpriority="high" decoding="async"/>'
        '<h1 class="ssr-title">%s</h1>'
        '<div class="ssr-price">%s</div>'
        '<div class="ssr-stock">%s</div>'
        '<div class="ssr-desc">%s</div>'
    ) % (
        ' › '.join(crumb), _esc(img_disp), _esc(name), _esc(name), price_html,
        ('متوفر' if in_stock else 'غير متوفر حاليًا') if is_ar
        else ('In stock' if in_stock else 'Out of stock'),
        _esc(full_desc),
    )

    pjson = json.dumps(p, ensure_ascii=False).replace('</', '<\\/')
    page = (html
            .replace('/*__P__*/null', pjson.replace('/image_1920', '/image_1024'))
            .replace('__PID__', str(int(pid)))
            .replace('__HEAD__', head)
            .replace('__VID__', str(int(variant_id)))
            .replace('__SSR__', ssr))
    return request.make_response(page, headers=[
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Cache-Control', 'private, max-age=30'),
        ('Vary', 'User-Agent'),
    ])


class UcMobileProduct(http.Controller):

    @http.route(['/m/p/<int:pid>'], type='http', auth='public', website=True,
                sitemap=False, readonly=True)
    def mobile_product(self, pid, **kw):
        tmpl = request.env['product.template'].sudo().browse(int(pid)).exists()
        # /m/p is the preview/alias route -> noindex (the canonical /shop URL is indexed)
        return render_app_product(tmpl, noindex=True)

    @http.route('/uc/me', type='json', auth='public', website=True)
    def uc_me(self, **kw):
        user = request.env.user
        return {'auth': not user._is_public(),
                'wishlist': list(request.session.get('uc_wishlist', []))}

    @http.route('/uc/wish', type='json', auth='public', website=True)
    def uc_wish(self, product_id=None, on=None, **kw):
        if request.env.user._is_public():
            return {'need_login': True}
        wl = list(request.session.get('uc_wishlist', []))
        try:
            pid = int(product_id)
        except Exception:
            return {'wishlist': wl}
        if on and pid not in wl:
            wl.append(pid)
        elif not on and pid in wl:
            wl.remove(pid)
        request.session['uc_wishlist'] = wl
        return {'wishlist': wl}


class WebsiteSaleMobile(WebsiteSale):
    """On phones, serve the app-style page at the SAME /shop URL (SEO-safe)."""

    def product(self, product, category='', search='', **kwargs):
        try:
            if (kwargs.get('full') != '1'
                    and request.httprequest.cookies.get('m_full') != '1'
                    and _is_phone()
                    and _takeover_enabled()
                    and product and product.exists()
                    and product.is_published):
                return render_app_product(product.sudo())
        except Exception:
            pass
        return super().product(product, category=category, search=search, **kwargs)
