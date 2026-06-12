"""Hooks for sitemap + redirect dispatch + non-target locale deindex.

- Adds landing-page entries to website._enumerate_pages
- Wires the SEO redirect manager into `ir.http._serve_fallback`
- v2.0.40: injects `X-Robots-Tag: noindex, follow` header on pages served
  under non-target locale prefixes (fa, et, it, hi, de, fr, sv, sq, tr,
  es, bn). Google honors X-Robots-Tag exactly like a meta noindex, so
  this triggers gradual deindex without serving 4xx (no Domain Authority
  hit, no broken-page user experience).
"""
from odoo import models
from odoo.http import request


# Locales whose existing Google index we want to deprecate gracefully.
# Edit this set if marketing expands or narrows target geographies.
DEINDEX_LANG_PREFIXES = (
    'fa', 'et', 'it', 'hi', 'de', 'fr', 'sv', 'sq', 'tr', 'es', 'bn',
)


def _is_deindex_request():
    """True iff the current request is in a non-target locale, based on
    either the URL prefix (Odoo strips this before dispatch sometimes)
    OR the resolved request.lang_id / context lang."""
    # 1) URL prefix check on the *raw* incoming path (before website
    # middleware rewrites). Werkzeug exposes this via PATH_INFO before
    # any locale handling.
    try:
        raw_path = request.httprequest.environ.get('werkzeug.request_path') \
                or request.httprequest.path or '/'
        if raw_path[0] == '/' and len(raw_path) > 3:
            second = raw_path.find('/', 1)
            head = raw_path[1:second] if second > 0 else raw_path[1:]
            if head in DEINDEX_LANG_PREFIXES:
                return True
    except Exception:
        pass
    # 2) Check the original incoming URL — werkzeug preserves the locale
    # there even after Odoo rewrites the path internally.
    try:
        full = request.httprequest.environ.get('RAW_URI') \
            or request.httprequest.url or ''
        for lng in DEINDEX_LANG_PREFIXES:
            # Match /xx/ or /xx?... or trailing /xx
            if f'/{lng}/' in full or full.endswith(f'/{lng}'):
                return True
    except Exception:
        pass
    # 3) Check the resolved language code (after Odoo's locale resolution).
    try:
        lang = (request.env.context.get('lang') or '').split('_')[0]
        if lang in DEINDEX_LANG_PREFIXES:
            return True
    except Exception:
        pass
    return False


class Website(models.Model):
    _inherit = 'website'

    def _enumerate_pages(self, query_string=None, force=False):
        """Yield SEO landing pages on top of the default Odoo enumeration.

        Note: the sitemap iteration in Odoo's `sitemap_xml` itself reads
        `language_ids` from the website and renders one entry per lang
        per URL. To exclude non-target langs from the sitemap, we filter
        them on `_get_alternate_languages` (Odoo 18 hook) below."""
        for url in super()._enumerate_pages(query_string=query_string, force=force):
            yield url
        # The /app download landing page is a hand-built controller route
        # (website=False, sitemap=False), so Odoo never lists it. Surface it
        # in the sitemap so Google can index "Uellow App / تطبيق يلو".
        app_loc = "/app"
        if not query_string or query_string.lower() in app_loc.lower():
            yield {
                'loc': app_loc,
                'priority': 0.9,
                'changefreq': 'weekly',
            }
        SP = self.env.get('uellow.seo.page')
        if SP is None:
            return
        for page in SP.sudo().search([
            ('state', '=', 'published'), ('active', '=', True),
        ]):
            loc = f"/guides/{page.slug}"
            if query_string and query_string.lower() not in loc.lower():
                continue
            yield {
                'loc': loc,
                'priority': 0.75,
                'changefreq': 'weekly',
                'lastmod': page.write_date and page.write_date.date(),
            }


class Lang(models.Model):
    _inherit = 'res.lang'

    def _get_frontend(self):
        """Filter the frontend language list shown to crawlers via the
        hreflang link tags and the language switcher. Keeps non-target
        locales working when typed directly (no 4xx) but hides them from
        SEO + UI — necessary complement to X-Robots-Tag for clean
        deindex over 6-12 weeks."""
        full = super()._get_frontend()
        try:
            from odoo.addons.base.models.res_lang import LangDataDict
            kept = {code: data for code, data in full.items()
                    if (code.split('_')[0] not in DEINDEX_LANG_PREFIXES)}
            return LangDataDict(kept)
        except Exception:
            return full


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_fallback(cls):
        """Check redirect manager BEFORE Odoo's default 404 page.

        Odoo calls _serve_fallback only when normal route matching failed,
        so this is safe — we won't shadow any legitimate page.
        """
        path = request.httprequest.path or '/'
        rule = request.env['uellow.seo.redirect'].sudo().search(
            [('source_url', '=', path), ('active', '=', True)],
            limit=1,
        )
        if rule:
            rule.record_hit()
            return request.redirect(rule.target_url, code=int(rule.redirect_type or 301))
        return super()._serve_fallback()

    @classmethod
    def _post_dispatch(cls, response):
        """Inject `X-Robots-Tag: noindex, follow` on deindex-target locales.

        Google treats the header identically to a <meta name="robots"
        content="noindex,follow"> — and it works for non-HTML responses
        too. The page still returns 200 OK so users typing the URL aren't
        broken; only crawlers are signaled to drop the page from the index.
        Hooked in `_post_dispatch` (not `_dispatch`) so it runs after the
        response is fully formed and headers are mutable."""
        try:
            if _is_deindex_request() and response is not None and hasattr(response, 'headers'):
                response.headers['X-Robots-Tag'] = 'noindex, follow'
        except Exception:
            pass
        return super()._post_dispatch(response)
