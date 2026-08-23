# -*- coding: utf-8 -*-
"""App-faithful mobile HOME page — a carbon copy of the Flutter app home,
driven by the SAME builder (`mobile.page` slug='home' from uellow_mobile_pages).

On PHONES the website root (served via /home-preview) renders the builder's
resolved blocks — so any edit made in the app page builder shows on the website
too. Desktop keeps the classic home. SSR head + crawlable product links +
JSON-LD for SEO; the rich block UI hydrates client-side from `window.__HOME__`
(and re-fetches /api/mobile/v2/pages/home for freshness).

Kill switch: ir.config_parameter `uellow.m_home_enabled` = '0'.
Escape: ?full=1 (cookie m_full).
"""
import json
import os

from odoo import http
from odoo.http import request
from odoo.addons.uellow_home_slider.controllers.home_page import UellowHomePageController
from odoo.addons.uellow_theme.controllers.uc_mobile_product import (
    _esc, _loc, _money, _is_phone,
)

_HTML = {"src": None, "mtime": 0}


def _home_enabled():
    return request.env['ir.config_parameter'].sudo().get_param(
        'uellow.m_home_enabled', '1') not in ('0', 'false', 'False')


def _load_home_html():
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "static", "src", "m", "home.html"))
    st = os.stat(path)
    if _HTML["src"] is None or _HTML["mtime"] != st.st_mtime:
        with open(path, "r", encoding="utf-8") as f:
            _HTML["src"] = f.read()
        _HTML["mtime"] = st.st_mtime
    return _HTML["src"]


def _iter_items(blocks):
    """Yield every product item across all blocks (for SSR links + ItemList)."""
    seen = set()
    for b in blocks or []:
        data = b.get('data') or {}
        items = data.get('items') if isinstance(data, dict) else None
        for it in (items or []):
            if not isinstance(it, dict):
                continue
            pid = it.get('id')
            if pid in seen:
                continue
            seen.add(pid)
            yield it


def render_app_home(noindex=False):
    lang = request.env.context.get('lang') or request.env.lang or 'ar_001'
    is_ar = bool(lang and lang.startswith('ar'))
    base = request.httprequest.host_url.rstrip('/')
    https = base.replace('http://', 'https://')

    Page = request.env['mobile.page'].sudo()
    page = (Page.search([('slug', '=', 'home'), ('website_ids', 'in', [request.website.id])], limit=1)
            or Page.search([('slug', '=', 'home'), ('website_ids', '=', False)], limit=1)
            or Page.search([('slug', '=', 'home')], limit=1))
    if not page:
        return None
    # FAST path: only the cheap theme + seo (NOT the ~1.5–7s full block resolve).
    # The rich blocks hydrate client-side from the cached /api/mobile/v2/pages/home
    # (the same builder source the app uses), so the HTML ships instantly.
    theme = page._theme_dict()
    seo = {'title': page._tr(lang, 'seo_title'),
           'description': page._tr(lang, 'seo_description'),
           'image': page.seo_image}
    # cheap top-products query — for crawlable SSR links + ItemList only
    cid = request.env.company.id
    prods = request.env['product.template'].sudo().search(
        [('is_published', '=', True), ('website_published', '=', True),
         ('sale_ok', '=', True), ('company_id', 'in', [False, cid])],
        limit=30, order='website_sequence, id desc')
    items = [{
        'id': p.id, 'name': {'ar': p.name, 'en': p.name},
        'url': p.website_url or ('/shop/%s' % p.id),
        'image': '%s/web/image/product.template/%s/image_512?unique=%s' % (
            https, p.id, (p.write_date or p.create_date).strftime('%Y%m%d%H%M%S') if (p.write_date or p.create_date) else ''),
        'price': {'amount': round(float(p.list_price or 0), 3),
                  'symbol': ('د.ك' if is_ar else 'KD')},
    } for p in prods]

    # ── SEO head ──
    site = 'Uellow يلو'
    meta_title = _loc(seo.get('title'), lang) or (
        'يلو — تسوّق أونلاين في الكويت | Uellow' if is_ar
        else 'Uellow — Shop online in Kuwait')
    meta_desc = _loc(seo.get('description'), lang) or (
        'تسوّق أحدث المنتجات والعروض على يلو مع توصيل سريع داخل الكويت.'
        if is_ar else 'Shop the latest products and deals on Uellow — fast delivery across Kuwait.')
    canon = https + '/'
    wid = request.website.id if request.website else 1
    og_img = (items[0]['image'] if items and items[0].get('image')
              else (_loc(seo.get('image'), lang) or (https + '/web/image/website/%s/logo' % wid)))

    org = {"@context": "https://schema.org", "@type": "Organization",
           "name": site, "url": https + "/", "logo": https + "/web/image/website/%s/logo" % wid}
    website = {"@context": "https://schema.org", "@type": "WebSite",
               "name": site, "url": https + "/",
               "potentialAction": {"@type": "SearchAction",
                                   "target": https + "/shop?search={search_term_string}",
                                   "query-input": "required name=search_term_string"}}
    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "url": https + (it.get('url') or '/shop'),
                     "name": _loc(it.get('name'), lang)}
                    for i, it in enumerate(items[:30])]}
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
    preload = ('<link rel="preload" as="image" href="%s" fetchpriority="high"/>' % _esc(og_img)) if og_img else ''
    head = ''.join([
        '<title>%s</title>' % _esc(meta_title),
        '<meta name="description" content="%s"/>' % _esc(meta_desc),
        '<meta name="robots" content="%s"/>' % robots,
        '<link rel="canonical" href="%s"/>' % _esc(canon),
        hreflang, preload,
        '<meta property="og:type" content="website"/>',
        '<meta property="og:site_name" content="%s"/>' % _esc(site),
        '<meta property="og:locale" content="%s"/>' % ('ar_KW' if is_ar else 'en_US'),
        '<meta property="og:title" content="%s"/>' % _esc(meta_title),
        '<meta property="og:description" content="%s"/>' % _esc(meta_desc),
        '<meta property="og:image" content="%s"/>' % _esc(og_img),
        '<meta property="og:url" content="%s"/>' % _esc(canon),
        '<meta name="twitter:card" content="summary_large_image"/>',
        _ld(org), _ld(website), _ld(itemlist),
    ])

    # ── SSR crawlable body: heading + real product links (fast, one query) ──
    ssr = ['<h1 class="ssr-h1">%s</h1>' % _esc(
        site + (' — تسوّق أونلاين في الكويت' if is_ar else ' — Shop online in Kuwait'))]
    for it in items:
        nm = _loc(it.get('name'), lang)
        pr = it.get('price') or {}
        ssr.append(
            '<a class="ssr-card" href="%s"><img src="%s" alt="%s" loading="lazy" width="180" height="180"/>'
            '<span class="ssr-cn">%s</span><span class="ssr-cp">%s %s</span></a>' % (
                _esc(it.get('url') or '/shop'), _esc(it.get('image') or ''), _esc(nm),
                _esc(nm), _money(pr.get('amount')), _esc(pr.get('symbol') or '')))
    ssr_html = ''.join(ssr)

    embed = {'theme': theme, 'ar': is_ar, 'currency': ('د.ك' if is_ar else 'KD'),
             'logo': https + '/web/image/website/%s/logo' % wid}
    html = _load_home_html()
    html = (html
            .replace('/*__HOME__*/null', json.dumps(embed, ensure_ascii=False).replace('</', '<\\/'))
            .replace('__HEAD__', head)
            .replace('__SSR__', ssr_html))
    return request.make_response(html, headers=[
        ('Content-Type', 'text/html; charset=utf-8'),
        ('Cache-Control', 'private, max-age=30'),
        ('Vary', 'User-Agent'),
    ])


class WebsiteHomeMobile(UellowHomePageController):

    @http.route('/uc/account_menu', type='http', auth='public', website=True,
                sitemap=False, csrf=False)
    def uc_account_menu(self, **kw):
        """Live account/drawer config (same data the premium mobile drawer uses)."""
        website = request.website
        user = request.env.user
        try:
            is_guest = user._is_public()
        except Exception:
            is_guest = True
        xlang = (request.httprequest.headers.get('X-Lang') or '').lower()
        if xlang.startswith('ar'):
            lang, is_ar = 'ar_001', True
        elif xlang.startswith('en'):
            lang, is_ar = 'en_US', False
        else:
            lang = request.env.context.get('lang') or request.env.lang or 'en_US'
            is_ar = bool(lang and lang.startswith('ar'))

        data = {
            'ar': is_ar,
            'user': {
                'guest': is_guest,
                'name': ('' if is_guest else (user.name or '')),
                'email': ('' if is_guest else (user.login or '')),
                'avatar': ('' if is_guest else ('/web/image/res.users/%s/avatar_128' % user.id)),
            },
            'wishlist': 0,
            'brands': [], 'menus': [], 'socials': [], 'service': [], 'policies': [],
            'app': {}, 'phone': '', 'storefront': website.name or 'Uellow',
        }
        if not is_guest:
            try:
                data['wishlist'] = len(request.env['product.wishlist'].current())
            except Exception:
                pass
        try:
            for b in website.sudo()._get_brands(limit=12):
                data['brands'].append({
                    'id': b.id, 'name': b.name,
                    'image': ('/web/image/product.attribute.value/%s/dr_image' % b.id) if b.dr_image else '',
                })
        except Exception:
            pass
        try:
            for m in website.menu_id.child_id.with_context(lang=lang):
                if m.url and m.url not in ('#', ''):
                    data['menus'].append({'name': m.name, 'url': m.url})
        except Exception:
            pass
        try:
            for so in (website.sudo()._uc_socials() or []):
                if so.get('url'):
                    data['socials'].append({'icon': so.get('icon'), 'url': so.get('url'),
                                            'label': so.get('label')})
        except Exception:
            pass
        try:
            data['app'] = {'ios': website.uc_app_ios_url or '', 'android': website.uc_app_android_url or ''}
        except Exception:
            data['app'] = {}
        try:
            data['phone'] = website.company_id.phone or ''
        except Exception:
            pass
        # Real, working help/policy pages only (no /page/faq 404s) — scan published pages.
        try:
            pol_kw = ['privacy', 'terms', 'cookie', 'policy', 'legal', 'condition', 'refund', 'return']
            help_kw = ['faq', 'shipping', 'deliver', 'track', 'support', 'help', 'about', 'warranty']
            pages = request.env['website.page'].sudo().search(
                [('is_published', '=', True), ('url', '!=', False)])
            seen = set()
            for pg in pages:
                u = (pg.url or '').strip()
                if not u.startswith('/') or u in seen:
                    continue
                nm = (pg.name or u).strip()
                low = (u + ' ' + nm).lower()
                if any(k in low for k in pol_kw):
                    seen.add(u); data['policies'].append({'name': nm, 'url': u})
                elif any(k in low for k in help_kw):
                    seen.add(u); data['service'].append({'name': nm, 'url': u})
        except Exception:
            pass
        # Contact us always first in service (route always exists)
        data['service'].insert(0, {'name': ('\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0646\u0627' if is_ar else 'Contact us'), 'url': '/contactus'})
        return request.make_response(
            json.dumps({'data': data}, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8'),
                     ('Cache-Control', 'private, max-age=60')])

    def home_preview(self, **kw):
        try:
            if (kw.get('full') != '1'
                    and request.httprequest.cookies.get('m_full') != '1'
                    and _is_phone() and _home_enabled()):
                resp = render_app_home()
                if resp is not None:
                    return resp
        except Exception:
            pass
        resp = super().home_preview(**kw)
        # The homepage is served per-device (phone → app home, desktop → classic).
        # Force it non-shared-cacheable + Vary so the CDN can't serve one device's
        # HTML to the other. (The mobile response already sets these.)
        try:
            if hasattr(resp, 'headers'):
                resp.headers['Cache-Control'] = 'private, max-age=60'
                if 'User-Agent' not in (resp.headers.get('Vary') or ''):
                    resp.headers['Vary'] = ((resp.headers.get('Vary') + ', ')
                                            if resp.headers.get('Vary') else '') + 'User-Agent'
        except Exception:
            pass
        return resp
