# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class UcMegaMenu(http.Controller):
    """Lazy category mega-panel — the header renders only the first panel inline;
    the rest are fetched here on hover so every page ships a much lighter DOM."""

    @http.route('/uc/megapanel', type='http', auth='public', website=True,
                sitemap=False, readonly=True)
    def megapanel(self, cat=None, **kw):
        try:
            rec = request.env['product.public.category'].sudo().browse(int(cat)).exists()
        except Exception:
            rec = None
        if not rec:
            return request.make_response(
                '', headers=[('Content-Type', 'text/html; charset=utf-8')])
        html = request.env['ir.qweb']._render('uellow_theme.uc_catmega_panel', {
            '_cat': rec,
            'website': request.website,
        })
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'public, max-age=300'),
        ])
