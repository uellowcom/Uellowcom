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

import hashlib
import os
import tempfile
import time as _time

# Cross-worker shared cache for resolved public pages (survives per-worker
# cold starts: every Odoo worker process shares the container filesystem).
_SHARED_CACHE_DIR = '/tmp/uc_pagecache'
_SHARED_TTL = 600


def _sc_path(cache_key):
    h = hashlib.md5(repr(cache_key).encode('utf-8')).hexdigest()
    return os.path.join(_SHARED_CACHE_DIR, h + '.json')


def _shared_get(cache_key, ttl=_SHARED_TTL):
    try:
        p = _sc_path(cache_key)
        if _time.time() - os.stat(p).st_mtime < ttl:
            with open(p, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _shared_set(cache_key, payload):
    try:
        os.makedirs(_SHARED_CACHE_DIR, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=_SHARED_CACHE_DIR)
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f, default=str)
        os.replace(tmp, _sc_path(cache_key))
    except Exception:
        pass


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


def _website_id():
    """Website scoping — the app sends X-Website-Id (or ?website_id=).
    Returns int id or None. Every public builder endpoint honours it so
    each website gets its OWN pages / navbar / designs."""
    try:
        wid = int(request.httprequest.headers.get('X-Website-Id')
                  or request.httprequest.args.get('website_id') or 0)
        if wid:
            return wid
    except Exception:
        pass
    # Fallback: resolve the per-country website by HOST so each subdomain
    # (ae/sa/kw...) gets its OWN resolved+cached blocks (local currency).
    try:
        host = (request.httprequest.headers.get('X-Forwarded-Host')
                or request.httprequest.host or '').split(':')[0].lower()
        if host and 'localhost' not in host and '127.0' not in host:
            w = request.env['website'].sudo().search([('domain', 'ilike', host)], limit=1)
            if w:
                return w.id
    except Exception:
        pass
    return None


class PagesPublic(http.Controller):

    @http.route('/api/mobile/v2/pages', type='http', auth='public',
                methods=['GET'], csrf=False)
    def list_pages(self, **kw):
        country_code = _country_code()
        dom = [('status', '=', 'published')]
        if country_code:
            dom += ['|', ('country_ids', '=', False),
                    ('country_ids.code', '=', country_code)]
        wid = _website_id()
        if wid:
            # Pages targeted to this website + untargeted (global) pages.
            dom += ['|', ('website_ids', '=', False), ('website_ids', 'in', [wid])]
        recs = request.env['mobile.page'].sudo().search(dom)
        return _ok({
            'pages': [{
                'id': r.id, 'slug': r.slug, 'kind': r.kind,
                'name': r.with_context(lang=_lang()).name or r.name,
                'pinned': r.pinned,
                'theme_code': r.theme_preset_id and r.theme_preset_id.code,
            } for r in recs]
        })

    # v2.1.48 — short worker-local cache for resolved PUBLIC pages.
    # Resolving every block (products, ranks, promos…) on every app open
    # made startup feel heavy; page content tolerates 45 s of staleness.
    _PAGE_CACHE = {}

    @http.route('/api/mobile/v2/pages/<string:slug>', type='http',
                auth='public', methods=['GET'], csrf=False)
    def get_page(self, slug, **kw):
        import time as _t
        wid = _website_id()
        cache_key = (slug, wid, _lang(), _country_code())
        # Local warmer may force a fresh resolve to keep the shared cache
        # hot. Gated to loopback with no X-Forwarded-For so the public
        # (always proxied via CF/nginx → XFF present) can't trigger it.
        _warm = (kw.get('_refresh') == '1'
                 and request.httprequest.remote_addr in ('127.0.0.1', '::1')
                 and not request.httprequest.headers.get('X-Forwarded-For'))
        hit = self._PAGE_CACHE.get(cache_key)
        # v2.2.x — TTL raised 45→120s. Resolving every block (products,
        # ranks, promos…) costs ~1s warm but balloons to 5s under crawler
        # CPU contention, and a cold rebuild every 45s per worker was making
        # the app hang / time out. 120s cuts cold builds ~3×; staff/editors
        # bypass the cache (group_user) so Builder edits still show instantly.
        if not _warm and hit and _t.time() - hit[1] < 600 \
                and not request.env.user.has_group('base.group_user'):
            return _ok(hit[0])
        # Cross-worker fallback: a cold worker serves the shared on-disk
        # payload (~ms) instead of rebuilding every block (~5s).
        if not _warm and not request.env.user.has_group('base.group_user'):
            _shared = _shared_get(cache_key)
            if _shared is not None:
                self._PAGE_CACHE[cache_key] = (_shared, _t.time())
                return _ok(_shared)
        rec = request.env['mobile.page'].sudo().browse([])
        if wid:
            # Same slug may exist per-website with a different design —
            # prefer the page explicitly targeted to this website.
            rec = request.env['mobile.page'].sudo().search(
                [('slug', '=', slug), ('website_ids', 'in', [wid])], limit=1)
        if not rec:
            rec = request.env['mobile.page'].sudo().search(
                [('slug', '=', slug), ('website_ids', '=', False)], limit=1)
        if not rec:
            rec = request.env['mobile.page'].sudo().search(
                [('slug', '=', slug)], limit=1)
        if not rec:
            return _fail('NOT_FOUND', 'Page not found', 404)
        if rec.status != 'published' and not request.env.user.has_group('base.group_user'):
            return _fail('NOT_PUBLISHED', 'Page is not live yet', 403)
        payload = rec.to_public_dict(lang=_lang())
        if rec.status == 'published':
            self._PAGE_CACHE[cache_key] = (payload, _t.time())
            _shared_set(cache_key, payload)
            if len(self._PAGE_CACHE) > 400:
                stale = sorted(self._PAGE_CACHE,
                               key=lambda k: self._PAGE_CACHE[k][1])[:200]
                for k in stale:
                    self._PAGE_CACHE.pop(k, None)
        return _ok(payload)

    @http.route('/api/mobile/v2/navbar', type='http', auth='public',
                methods=['GET'], csrf=False)
    def get_navbar(self, **kw):
        website_id = _website_id() or (
            getattr(request, 'website', None) and request.website.id or None)
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
