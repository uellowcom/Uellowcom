"""SEO controllers: robots.txt, dedicated sitemap for landing pages, redirects.

Why a dedicated sitemap?
  Odoo's default /sitemap.xml does include our landing pages now (we hook
  `_enumerate_pages`), but we also expose /sitemap-pages.xml so marketing
  can point Google Search Console at the landing-pages set independently.
"""
from datetime import datetime, date
import logging
import re

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class SEOController(http.Controller):

    # ──────────────────────────────────────────────────────────────────
    # robots.txt — content lives in uellow.seo.config so marketing edits
    # it in the UI without filesystem access.
    # ──────────────────────────────────────────────────────────────────
    @http.route('/robots.txt', type='http', auth='public', website=True, sitemap=False)
    def robots(self, **kw):
        cfg = request.env['uellow.seo.config'].sudo().get_config()
        body = cfg.robots_txt or (
            'User-agent: *\n'
            'Allow: /\n'
            'Sitemap: /sitemap.xml\n'
        )
        return Response(body, mimetype='text/plain; charset=utf-8')

    # ──────────────────────────────────────────────────────────────────
    # Dedicated sitemap for SEO landing pages.
    # ──────────────────────────────────────────────────────────────────
    @http.route('/sitemap-pages.xml', type='http', auth='public', website=True, sitemap=False)
    def sitemap_pages(self, **kw):
        base = (request.env['ir.config_parameter'].sudo()
                .get_param('web.base.url') or '').rstrip('/')
        SP = request.env.get('uellow.seo.page')
        urls = []
        if SP is not None:
            pages = SP.sudo().search([
                ('state', '=', 'published'),
                ('active', '=', True),
            ])
            for p in pages:
                lastmod = (p.write_date or datetime.now()).date().isoformat()
                urls.append(
                    f'<url>'
                    f'<loc>{base}/guides/{p.slug}</loc>'
                    f'<lastmod>{lastmod}</lastmod>'
                    f'<changefreq>weekly</changefreq>'
                    f'<priority>0.75</priority>'
                    f'</url>'
                )
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + '\n'.join(urls) +
            '\n</urlset>\n'
        )
        return Response(body, mimetype='application/xml; charset=utf-8')

    # NB: 301/302 redirects are dispatched via website inherit hook
    # (`models/website_inherit.py` → `ir.http._serve_fallback`) so they
    # only fire on real 404s and never hijack legitimate routes.
