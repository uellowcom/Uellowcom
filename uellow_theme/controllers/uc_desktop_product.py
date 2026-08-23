# -*- coding: utf-8 -*-
"""Professional desktop product page rendered INSIDE the real website.layout.

On desktop (non-phone) the /shop product page serves the new data-driven design as a
scoped fragment (#uc-dpd) injected into website.layout -> it inherits the REAL site
header, footer, mega-menu, search and cart (identical to the homepage), while the
product body is hydrated client-side from window.__P__ (same serializer as the app).

Rollout: kill switch ir.config_parameter uellow.d_product_enabled (default 0 = OFF);
preview /shop/<slug>?dnew=1; escape /shop/<slug>?classic=1 or cookie d_classic=1.
Phones keep the app-style page (WebsiteSaleMobile, our super()).
"""
import json
import re
import html as _html
import os

from markupsafe import Markup

from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale  # noqa: F401
from .uc_mobile_product import (
    WebsiteSaleMobile, _is_phone, _loc, serialize_product_full,
)

_FRAG = {"src": None, "mtime": 0}


def _load_frag():
    path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "static", "src", "d", "product_frag.html"))
    st = os.stat(path)
    if _FRAG["src"] is None or _FRAG["mtime"] != st.st_mtime:
        with open(path, "r", encoding="utf-8") as f:
            _FRAG["src"] = f.read()
        _FRAG["mtime"] = st.st_mtime
    return _FRAG["src"]


def _d_enabled():
    return request.env["ir.config_parameter"].sudo().get_param(
        "uellow.d_product_enabled", "0") == "1"


def _ld_tag(d):
    return '<script type="application/ld+json">%s</script>' % (
        json.dumps(d, ensure_ascii=False).replace("</", "<\\/"))


def _jsonld(tmpl, p, lang, canon, name, price, cur, in_stock):
    is_ar = bool(lang and lang.startswith("ar"))
    try:
        product_ld = request.env["uellow.seo.product"].sudo()._build_product_jsonld(
            tmpl, tmpl.with_context(lang="en_US"))
    except Exception:
        product_ld = {
            "@context": "https://schema.org", "@type": "Product", "name": name,
            "sku": p.get("sku") or str(tmpl.id), "url": canon,
            "offers": {"@type": "Offer", "price": "%.3f" % float(price or 0),
                       "priceCurrency": cur, "url": canon,
                       "availability": "https://schema.org/%s" % (
                           "InStock" if in_stock else "OutOfStock")}}
    try:
        product_ld.setdefault("url", canon)
        if isinstance(product_ld.get("offers"), dict):
            product_ld["offers"].setdefault("url", canon)
    except Exception:
        pass
    try:
        if isinstance(product_ld.get("offers"), dict) and p.get("price"):
            product_ld["offers"]["price"] = "%.3f" % float(p["price"]["amount"])
            product_ld["offers"]["priceCurrency"] = p["price"]["currency"]
    except Exception:
        pass
    shop = canon.rsplit("/shop", 1)[0] + "/shop"
    crumbs = [{"@type": "ListItem", "position": 1,
               "name": ("المتجر" if is_ar else "Shop"), "item": shop}]
    if p.get("categories"):
        cn = _loc(p["categories"][0].get("name"), lang)
        if cn:
            crumbs.append({"@type": "ListItem", "position": 2, "name": cn, "item": shop})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1,
                   "name": name, "item": canon})
    breadcrumb_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                     "itemListElement": crumbs}
    return _ld_tag(product_ld) + _ld_tag(breadcrumb_ld)


def _build_fragment(tmpl):
    """Fill the scoped design fragment with real product data + JSON-LD."""
    lang = (request.env.context.get("lang") or "ar_001")
    tmpl = tmpl.sudo()
    p = serialize_product_full(tmpl, lang) if serialize_product_full else {}
    # Localize price to the website's pricelist currency (per-country stores
    # ae→AED, sa→SAR, om→OMR ...). Matches the native shop + checkout, and
    # makes each country page genuinely distinct (fixes duplicate-canonical).
    try:
        _pl = None
        try:
            _pl = request.website._get_current_pricelist()
        except Exception:
            _pl = request.website.pricelist_id
        if _pl and _pl.currency_id and p.get('price'):
            from odoo import fields as _flds
            _plc = _pl.currency_id
            _var = tmpl.product_variant_id
            _amt = _pl._get_product_price(_var, 1.0)
            _sym = _plc.symbol or _plc.name
            p['price'] = {'amount': round(float(_amt), 3), 'symbol': _sym, 'currency': _plc.name}
            _cmp_kwd = float(getattr(tmpl, 'compare_list_price', 0) or 0)
            if _cmp_kwd and _cmp_kwd > float(tmpl.list_price or 0):
                _cmp_loc = tmpl.currency_id._convert(_cmp_kwd, _plc, request.env.company, _flds.Date.today())
                p['compare_price'] = {'amount': round(float(_cmp_loc), 3), 'symbol': _sym, 'currency': _plc.name}
    except Exception:
        pass
    name = _loc(p.get("name"), lang) or (tmpl.name or "")
    price = (p.get("price") or {}).get("amount") or 0
    cur = (p.get("price") or {}).get("currency") or "KWD"
    in_stock = bool(p.get("in_stock") or p.get("allow_out_of_stock_order"))
    try:
        variant_id = tmpl.product_variant_id.id if tmpl.product_variant_id else 0
    except Exception:
        variant_id = 0
    base = request.httprequest.host_url.rstrip("/").replace("http://", "https://")
    canon = base + (tmpl.website_url or "/shop")
    ld = _jsonld(tmpl, p, lang, canon, name, price, cur, in_stock)
    is_ar = "1" if (lang or "").startswith("ar") else "0"
    try:
        p["_faq"] = [{"q": q, "a": a} for (q, a) in (tmpl._seo_faqs() or [])]
    except Exception:
        p["_faq"] = []
    # warranty policy -> sidebar card (desktop)
    try:
        _wsite = None
        try:
            _wsite = request.website
        except Exception:
            _wsite = None
        _pol = tmpl._uellow_get_warranty_policy(_wsite)
        if _pol and not _pol.no_warranty and _pol.duration_months:
            _ar = (lang or "").startswith("ar")
            p["warranty"] = {
                "months": int(_pol.duration_months),
                "name": (_pol.name_ar or _pol.name) if _ar else _pol.name,
                "icon": _pol.icon or "🛡️",
                "coverage": (_pol.coverage_ar if _ar else _pol.coverage_en) or "",
            }
    except Exception:
        pass
    pjson = (json.dumps(p, ensure_ascii=False)
             .replace("</", "<\\/").replace("/image_1920", "/image_1024"))
    # anti-FOUC: in English, hide the (Arabic-authored) design until the i18n pass
    # translates it, then REVEAL_JS reveals it — no flash of Arabic before English.
    i18n_hide = ("" if is_ar == "1" else
                 "<style>#uc-dpd{visibility:hidden;opacity:0;"
                 "transition:opacity .2s ease}</style>")
    frag = (_load_frag()
            .replace("/*__P__*/null", pjson)
            .replace("__PID__", str(int(tmpl.id)))
            .replace("__VID__", str(int(variant_id)))
            .replace("__AR__", is_ar)
            .replace("__I18NHIDE__", i18n_hide)
            .replace("__LD__", ld))
    # SSR the REAL product name into the placeholder <h1> (SEO + standards)
    try:
        frag = re.sub(r"<h1>.*?</h1>", "<h1>" + _html.escape(name) + "</h1>",
                      frag, count=1, flags=re.S)
    except Exception:
        pass
    # SSR the REAL price block (was a mockup placeholder) for standards/UX/SEO
    try:
        _sym = (p.get('price') or {}).get('symbol') or 'د.ك'
        _now = '%.3f' % float(price or 0)
        _cmp = float((p.get('compare_price') or {}).get('amount') or 0)
        _ph = ('<div class="pl"><div class="now tnum">5.250<span class="c"> د.ك</span></div>'
               '<div class="was tnum">7.500</div><div class="off">-٣٠٪</div>'
               '<div class="save">وفّرت 2.250 د.ك</div></div>')
        if _cmp > float(price or 0):
            _artr = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
            _off = str(int(round((1 - float(price) / _cmp) * 100))).translate(_artr)
            _sv = '%.3f' % (_cmp - float(price))
            _real = ('<div class="pl"><div class="now tnum">' + _now + '<span class="c"> ' + _sym + '</span></div>'
                     '<div class="was tnum">' + ('%.3f' % _cmp) + '</div>'
                     '<div class="off">-' + _off + '٪</div>'
                     '<div class="save">وفّرت ' + _sv + ' ' + _sym + '</div></div>')
        else:
            _real = ('<div class="pl"><div class="now tnum">' + _now + '<span class="c"> ' + _sym + '</span></div></div>')
        frag = frag.replace(_ph, _real, 1)
    except Exception:
        pass
    # SSR the REAL description (crawlers read SSR; the fragment ships a fixed
    # demo product body — replace it so title & content match).
    try:
        _desc = _loc(p.get('description_html'), lang) or _loc(p.get('description_short'), lang) or ''
        if _desc:
            frag = re.sub(
                r'(<h3>\u0648\u0635\u0641 \u0627\u0644\u0645\u0646\u062a\u062c</h3>)\s*<p>.*?</p>',
                lambda m: m.group(1) + '<div class="uc-desc" data-ssr="1">' + _desc + '</div>',
                frag, count=1, flags=re.S)
    except Exception:
        pass
    # SSR real specs rows from attributes (or drop the mockup specs table).
    try:
        _rows = ''
        for _a in (p.get('attributes') or []):
            _an = _loc(_a.get('attribute_name') or _a.get('name'), lang) or ''
            _vals = _a.get('values') or _a.get('options') or []
            _vs = ' \u00b7 '.join([_html.escape(_loc((_v.get('name') if isinstance(_v, dict) else _v), lang) or '') for _v in _vals])
            if _an and _vs:
                _rows += '<tr><td>' + _html.escape(_an) + '</td><td>' + _vs + '</td></tr>'
        if _rows:
            frag = re.sub(r'<table class="specs">.*?</table>',
                          lambda m: '<table class="specs">' + _rows + '</table>',
                          frag, count=1, flags=re.S)
        else:
            frag = re.sub(r'<h3 style="margin-top:20px">\u0627\u0644\u0645\u0648\u0627\u0635\u0641\u0627\u062a</h3>\s*<table class="specs">.*?</table>',
                          '', frag, count=1, flags=re.S)
    except Exception:
        pass
    return frag


class WebsiteSaleDesktop(WebsiteSaleMobile):
    """Desktop takeover; falls back to the mobile/classic chain via super().

    Renders the new design INSIDE the real product-page context: it reuses
    website_sale's own `_prepare_product_values` so the theme's layout components
    (header, footer, mobile bottombar, combination_info, ...) all get the full
    context they expect, then injects the scoped #uc-dpd design fragment.
    """

    def product(self, product, category="", search="", **kwargs):
        try:
            force = kwargs.get("dnew") == "1"
            if (kwargs.get("classic") != "1"
                    and request.httprequest.cookies.get("d_classic") != "1"
                    and not _is_phone()
                    and (force or _d_enabled())
                    and product and product.exists()
                    and product.is_published):
                vals = self._prepare_product_values(
                    product, category=category, search=search, **kwargs)
                if not vals.get("combination_info"):
                    try:
                        vals["combination_info"] = product._get_combination_info()
                    except Exception:
                        vals["combination_info"] = {"price": 0, "list_price": 0}
                vals["uc_fragment"] = Markup(_build_fragment(product.sudo()))
                vals.setdefault("main_object", product)
                return request.render("uellow_theme.uc_desktop_product_layout", vals)
        except Exception:
            pass
        return super().product(product, category=category, search=search, **kwargs)
