# -*- coding: utf-8 -*-
"""Public mobile API — what the Flutter app calls.

GET /api/mobile/v2/pages/<slug>   → one page (theme + blocks)
GET /api/mobile/v2/pages          → list of slugs (for prefetch)
GET /api/mobile/v2/navbar         → bottom nav config
GET /api/mobile/v2/themes         → all theme presets
"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _ok(data):
    # `Cache-Control: no-store` forces every Builder publish to be visible
    # on the next app fetch — Cloudflare otherwise caches JSON for hours
    # and stale-while-revalidate hides edits for a long time.
    return request.make_response(
        json.dumps({'success': True, 'data': data}, default=str),
        headers=[('Content-Type', 'application/json'),
                 ('Cache-Control', 'no-store, no-cache, must-revalidate'),
                 ('Pragma', 'no-cache'),
                 ('Access-Control-Allow-Origin', '*')])


def _fail(code, msg, status=400):
    return request.make_response(
        json.dumps({'success': False, 'error': {'code': code, 'message': msg}}),
        status=status,
        headers=[('Content-Type', 'application/json')])


def _lang():
    """Resolve the requesting client's language as an Odoo lang code.
    Accepts short ('en','ar') or full ('en_US','ar_001') from the client."""
    raw = (request.httprequest.headers.get('X-Lang')
           or request.httprequest.args.get('lang')
           or 'en').strip()
    if '_' in raw:
        return raw
    # Find an active Odoo lang whose code starts with the short form
    rec = request.env['res.lang'].sudo().search(
        [('active', '=', True), ('code', '=like', raw + '%')], limit=1)
    if rec:
        return rec.code
    return 'en_US'


def _country_code():
    return (request.httprequest.args.get('country')
            or request.httprequest.headers.get('CF-IPCountry')
            or '').upper()


class PagesPublic(http.Controller):

    @http.route('/api/mobile/v2/pages', type='http', auth='public',
                methods=['GET'], csrf=False)
    def list_pages(self, **kw):
        country_code = _country_code()
        dom = [('status', '=', 'published')]
        if country_code:
            dom += ['|', ('country_ids', '=', False),
                    ('country_ids.code', '=', country_code)]
        recs = request.env['mobile.page'].sudo().search(dom)
        return _ok({
            'pages': [{
                'id': r.id, 'slug': r.slug, 'kind': r.kind,
                'name': r.with_context(lang=_lang()).name or r.name,
                'pinned': r.pinned,
                'theme_code': r.theme_preset_id and r.theme_preset_id.code,
            } for r in recs]
        })

    @http.route('/api/mobile/v2/pages/<string:slug>', type='http',
                auth='public', methods=['GET'], csrf=False)
    def get_page(self, slug, **kw):
        rec = request.env['mobile.page'].sudo().search(
            [('slug', '=', slug)], limit=1)
        if not rec:
            return _fail('NOT_FOUND', 'Page not found', 404)
        if rec.status != 'published' and not request.env.user.has_group('base.group_user'):
            return _fail('NOT_PUBLISHED', 'Page is not live yet', 403)
        return _ok(rec.to_public_dict(lang=_lang()))

    @http.route('/api/mobile/v2/navbar', type='http', auth='public',
                methods=['GET'], csrf=False)
    def get_navbar(self, **kw):
        website_id = getattr(request, 'website', None) and request.website.id or None
        nav = request.env['mobile.navbar'].sudo().get_for(
            website_id=website_id, country_code=_country_code())
        if not nav:
            return _ok({'items': [], 'style': {}})
        return _ok(nav.to_public_dict(lang=_lang()))

    @http.route('/api/mobile/v2/themes', type='http', auth='public',
                methods=['GET'], csrf=False)
    def list_themes(self, **kw):
        recs = request.env['mobile.theme.preset'].sudo().search([])
        return _ok({'themes': [r.to_dict() for r in recs]})
