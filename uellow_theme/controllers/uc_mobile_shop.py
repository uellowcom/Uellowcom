# -*- coding: utf-8 -*-
"""App-faithful mobile SHOP / category-browse page.

Served on PHONES at the same /shop, /shop/page/<n>, /shop/category/<cat> URLs
(desktop keeps the classic page). SSR head + a real product grid + ItemList /
BreadcrumbList / Organization / WebSite JSON-LD for SEO; the rich interactive
grid + categories rail + filters hydrate client-side from the mobile API.
"""
import json
import os

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.uellow_theme.controllers.uc_mobile_product import (
    _esc, _loc, _money, _is_phone, _takeover_enabled,
)

_HTML = {"src": None, "mtime": 0}


def _load_shop_html():
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "static", "src", "m", "shop.html"))
    st = os.stat(path)
    if _HTML["src"] is None or _HTML["mtime"] != st.st_mtime:
        with open(path, "r", encoding="utf-8") as f:
            _HTML["src"] = f.read()
        _HTML["mtime"] = st.st_mtime
    return _HTML["src"]


def _cat_img(cat, base):
    if cat.image_128 or getattr(cat, 'image_1920', False):
        return '%s/web/image/product.public.category/%s/image_512' % (base, cat.id)
    return ''


def _cat_dict(cat, base, with_children=True):
    d = {'id': cat.id, 'name': cat.name, 'image': _cat_img(cat, base)}
    if with_children and cat.child_id:
        d['children'] = [{'id': ch.id, 'name': ch.name, 'image': _cat_img(ch, base)}
                         for ch in cat.child_id[:16]]
    return d


def render_app_shop(category=None, search='', noindex=False):
    lang = (request.env.context.get('lang') or 'ar_001')
    is_ar = bool(lang and lang.startswith('ar'))
    base = request.httprequest.host_url.rstrip('/')
    https = base.replace('http://', 'https://')
    Product = request.env['product.template'].sudo()
    Categ = request.env['product.public.category'].sudo()

    # ── top-level categories for the rail ──
    top = Categ.search([('parent_id', '=', False)], order='sequence, name', limit=30)
    cats = [_cat_dict(c, https) for c in top]

    # ── first page of products (SSR + embed) ──
    domain = [('is_published', '=', True), ('website_published', '=', True)]
    if category:
        domain.append(('public_categ_ids', 'child_of', category.id))
    if search:
        domain += ['|', ('name', 'ilike', search),
                   ('description_sale', 'ilike', search)]
    prods = Product.search(domain, limit=24, order='create_date desc, website_sequence')
    # website pricelist currency (per-country stores: ae->AED, sa->SAR ...)
    from odoo import fields as _flds
    try:
        _pl = request.website._get_current_pricelist()
    except Exception:
        _pl = request.website.pricelist_id
    _plc = _pl.currency_id if _pl else None
    _comp_cur = request.env.company.currency_id
    _cursym = (_plc.symbol or _plc.name) if _plc else ('د.ك' if is_ar else 'KD')
    _dt = _flds.Date.today()
    def _loc_price(_amt):
        try:
            if _plc and _comp_cur and _plc.id != _comp_cur.id:
                return round(float(_comp_cur._convert(float(_amt or 0), _plc, request.env.company, _dt)), 3)
        except Exception:
            pass
        return round(float(_amt or 0), 3)

    title_txt = (_loc(category.name, lang) if category else
                 (('نتائج: ' + search) if (search and is_ar) else
                  ('Results: ' + search) if search else
                  ('المتجر' if is_ar else 'Shop')))
    canon = https + (('/shop/category/%s' % category.id) if category else '/shop')

    # lightweight product list for the SSR grid + embed + ItemList
    plist = []
    for p in prods:
        cur = (p.currency_id.name if p.currency_id else 'KWD')
        cmp_amt = getattr(p, 'compare_list_price', 0) or 0
        plist.append({
            'id': p.id, 'name': p.name,
            'url': p.website_url or ('/shop'),
            'image': '%s/web/image/product.template/%s/image_512' % (https, p.id),
            'price': _loc_price(p.list_price or 0),
            'compare': _loc_price(cmp_amt) if cmp_amt and cmp_amt > p.list_price else 0,
            'currency': _cursym,
        })

    # ── SEO ──
    meta_title = (('%s | uellow يلو' % title_txt) if category or search
                  else ('المتجر · تسوّق أونلاين في الكويت | uellow يلو' if is_ar
                        else 'Shop online in Kuwait | uellow يلو'))
    meta_desc = (('تسوّق %s على يلو — أسعار ممتازة وتوصيل سريع داخل الكويت.' % title_txt)
                 if is_ar else
                 ('Shop %s on Uellow — great prices, fast delivery across Kuwait.' % title_txt))

    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "url": https + it['url'],
                     "name": _loc(it['name'], lang)}
                    for i, it in enumerate(plist[:20])]}
    crumbs = [{"@type": "ListItem", "position": 1,
               "name": ("الرئيسية" if is_ar else "Home"), "item": https + "/"},
              {"@type": "ListItem", "position": 2,
               "name": ("المتجر" if is_ar else "Shop"), "item": https + "/shop"}]
    if category:
        crumbs.append({"@type": "ListItem", "position": 3,
                       "name": _loc(category.name, lang), "item": canon})
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": crumbs}
    wid = request.website.id if request.website else 1
    org = {"@context": "https://schema.org", "@type": "Organization",
           "name": "Uellow يلو", "url": https + "/",
           "logo": https + "/web/image/website/%s/logo" % wid}
    website = {"@context": "https://schema.org", "@type": "WebSite",
               "name": "Uellow يلو", "url": https + "/",
               "potentialAction": {"@type": "SearchAction",
                                   "target": https + "/shop?search={search_term_string}",
                                   "query-input": "required name=search_term_string"}}
    hreflang = ''
    try:
        for hl in (request.website._uellow_country_hreflangs() or []):
            hreflang += '<link rel="alternate" hreflang="%s" href="%s"/>' % (
                _esc(hl.get('hreflang')), _esc(hl.get('href')))
    except Exception:
        hreflang = ''

    robots = 'noindex, follow' if noindex else \
        'index, follow, max-image-preview:large, max-snippet:-1'
    _ld = lambda d: '<script type="application/ld+json">%s</script>' % (
        json.dumps(d, ensure_ascii=False).replace('</', '<\\/'))
    og_img = (plist[0]['image'] if plist else (https + '/web/image/website/%s/logo' % wid))
    head = ''.join([
        '<title>%s</title>' % _esc(meta_title),
        '<meta name="description" content="%s"/>' % _esc(meta_desc),
        '<meta name="robots" content="%s"/>' % robots,
        '<link rel="canonical" href="%s"/>' % _esc(canon),
        hreflang,
        '<meta property="og:type" content="website"/>',
        '<meta property="og:site_name" content="Uellow يلو"/>',
        '<meta property="og:locale" content="%s"/>' % ('ar_KW' if is_ar else 'en_US'),
        '<meta property="og:title" content="%s"/>' % _esc(meta_title),
        '<meta property="og:description" content="%s"/>' % _esc(meta_desc),
        '<meta property="og:image" content="%s"/>' % _esc(og_img),
        '<meta property="og:url" content="%s"/>' % _esc(canon),
        '<meta name="twitter:card" content="summary_large_image"/>',
        '<meta name="twitter:title" content="%s"/>' % _esc(meta_title),
        _ld(itemlist), _ld(breadcrumb), _ld(org), _ld(website),
    ])

    # ── SSR grid (real links for crawlers) ──
    ssr_cards = ''
    for it in plist:
        pr = _money(it['price'])
        was = (' <s>%s</s>' % _money(it['compare'])) if it['compare'] else ''
        ssr_cards += (
            '<a class="ssr-card" href="%s"><img src="%s" alt="%s" loading="lazy" width="200" height="200"/>'
            '<div class="ssr-cn">%s</div><div class="ssr-cp">%s %s%s</div></a>'
        ) % (_esc(it['url']), _esc(it['image']), _esc(_loc(it['name'], lang)),
             _esc(_loc(it['name'], lang)), pr, _esc(it['currency']), was)
    ssr = ('<nav class="ssr-crumb"><a href="/">%s</a> › %s</nav>'
           '<h1 class="ssr-h1">%s</h1><div class="ssr-grid">%s</div>') % (
        ('الرئيسية' if is_ar else 'Home'),
        _esc(title_txt), _esc(title_txt), ssr_cards)

    # manual "Best sellers" selection (admin picks in mobile.app.setting)
    best = []
    try:
        setting = (request.env['mobile.app.setting'].sudo().search(
                       [('website_id', '=', wid)], limit=1)
                   or request.env['mobile.app.setting'].sudo().search([], limit=1))
        if setting and setting.shop_bestseller_manual and setting.shop_bestseller_product_ids:
            for p in setting.shop_bestseller_product_ids:
                if not p.is_published:
                    continue
                cmp_amt = getattr(p, 'compare_list_price', 0) or 0
                off = 0
                if cmp_amt and cmp_amt > p.list_price:
                    off = int(round((cmp_amt - p.list_price) / cmp_amt * 100))
                best.append({
                    'id': p.id, 'name': p.name,
                    'image': '%s/web/image/product.template/%s/image_512' % (https, p.id),
                    'price': {'amount': _loc_price(p.list_price or 0),
                              'symbol': _cursym},
                    'compare_price': ({'amount': _loc_price(cmp_amt)} if off else None),
                    'discount_pct': off,
                })
    except Exception:
        best = []

    embed = {
        'cats': cats,
        'products': plist,
        'bestsellers': best,
        'category_id': category.id if category else None,
        'category_name': _loc(category.name, lang) if category else None,
        'search': search or '',
        'title': title_txt,
        'ar': is_ar,
    }
    html = _load_shop_html()
    html = (html
            .replace('/*__SHOP__*/null', json.dumps(embed, ensure_ascii=False).replace('</', '<\\/'))
            .replace('__HEAD__', head)
            .replace('__SSR__', ssr))
    return request.make_response(html, headers=[
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Cache-Control', 'private, max-age=30'),
        ('Vary', 'User-Agent'),
    ])


class WebsiteSaleShopMobile(WebsiteSale):

    def shop(self, page=0, category=None, search='', min_price=0.0,
             max_price=0.0, ppg=False, **post):
        try:
            if (post.get('full') != '1'
                    and request.httprequest.cookies.get('m_full') != '1'
                    and _is_phone() and _takeover_enabled()):
                return render_app_shop(category=category, search=search or '')
        except Exception:
            pass
        return super().shop(page=page, category=category, search=search,
                            min_price=min_price, max_price=max_price, ppg=ppg, **post)
