"""Public controller for SEO landing pages.

Bugfixes vs. v1:
  - B6: route moved from `/l/<slug>` to `/guides/<slug>` (better SEO).
  - F7: only `published` pages are served publicly; staff can append
    `?preview=1` to view drafts.
  - A7: visit counter incremented via atomic SQL (in the model).
  - C5: counter only bumps for non-bot, non-preview hits.
"""
from datetime import datetime
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SEOPageController(http.Controller):

    @http.route('/guides', type='http', auth='public', website=True, sitemap=True)
    def seo_guides_index(self, **kw):
        pages = request.env['uellow.seo.page'].sudo().search([
            ('state', '=', 'published'),
            ('active', '=', True),
        ], order='sequence, id desc')
        return request.render('uellow_seo_pages.seo_guides_index', {'pages': pages})

    @http.route([
        '/guides/<string:slug>',
        # Keep legacy path alive as 301 to new path so existing links don't 404.
        '/l/<string:slug>',
    ], type='http', auth='public', website=True, sitemap=False)
    def seo_landing(self, slug, **kw):
        # Legacy redirect
        if request.httprequest.path.startswith('/l/'):
            return request.redirect(f'/guides/{slug}', code=301)

        preview = (kw.get('preview') == '1') and not request.env.user._is_public()
        domain = [('slug', '=', slug), ('active', '=', True)]
        if not preview:
            domain.append(('state', '=', 'published'))
        page = request.env['uellow.seo.page'].sudo().search(domain, limit=1)
        if not page:
            return request.not_found()

        # Skip counter for bots and preview hits.
        if not preview and not _looks_like_bot(request.httprequest):
            page.record_visit()

        products = page.get_products(page.max_products)
        lang_code = request.env.lang or 'en_US'
        title, h1, intro, meta_desc = page.localized(lang_code)

        return request.render('uellow_seo_pages.seo_landing_page', {
            'page':       page,
            'products':   products,
            'lang_code':  lang_code,
            'is_arabic':  lang_code.startswith('ar'),
            'title':      title,
            'h1':         h1,
            'intro':      intro,
            'meta_desc':  meta_desc,
            'preview':    preview,
        })


def _looks_like_bot(httprequest):
    ua = (httprequest.headers.get('User-Agent') or '').lower()
    if not ua:
        return True
    for marker in ('bot', 'crawler', 'spider', 'preview', 'fetch', 'curl', 'wget'):
        if marker in ua:
            return True
    return False
