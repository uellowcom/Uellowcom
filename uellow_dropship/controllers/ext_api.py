# -*- coding: utf-8 -*-
"""Chrome-extension import API.

The AliExpress DS feed API cannot search the catalog, so the extension runs ON
aliexpress.com, reads the product id(s) from the page, and calls these
key-protected endpoints to import them by id (which DOES work + pulls the full
detail). Two endpoints:

  POST /dropship/ext/import  {key, ids:[...], publish:bool}  -> import (+publish)
  POST /dropship/ext/check   {key, ids:[...]}                -> which already exist

All responses carry permissive CORS headers so the extension can call them
directly from the aliexpress.com origin (it also proxies through its background
service worker, which bypasses CORS via host_permissions).
"""
import io
import json
import logging
import os
import zipfile

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

_CORS = [
    ('Content-Type', 'application/json'),
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
    ('Access-Control-Allow-Headers', 'Content-Type, X-Uellow-Key'),
    ('Cache-Control', 'no-store'),
]


def _json(data, status=200):
    return request.make_response(
        json.dumps(data, default=str, ensure_ascii=False),
        headers=_CORS, status=status)


class DropshipExtApi(http.Controller):

    # ------------------------------------------------------------------ #
    def _icp(self):
        return request.env['ir.config_parameter'].sudo()

    def _authed(self, payload):
        """The extension sends the shared key (body or header)."""
        want = (self._icp().get_param('uellow_dropship.ext_api_key') or '').strip()
        if not want:
            return False
        got = (payload.get('key')
               or request.httprequest.headers.get('X-Uellow-Key') or '').strip()
        return got and got == want

    def _payload(self):
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            return json.loads(raw) if raw.strip() else {}
        except Exception:  # noqa: BLE001
            return {}

    @staticmethod
    def _clean_ids(ids):
        out = []
        for i in (ids or []):
            s = ''.join(ch for ch in str(i) if ch.isdigit())
            if len(s) >= 8 and s not in out:
                out.append(s)
        return out

    # ------------------------------------------------------------------ #
    @http.route('/dropship/ext/check', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    def ext_check(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({})
        p = self._payload()
        if not self._authed(p):
            return _json({'ok': False, 'error': 'bad key'}, status=401)
        ids = self._clean_ids(p.get('ids'))
        DP = request.env['dropship.product'].sudo()
        recs = DP.search([('source_id', 'in', ids)])
        by_sid = {r.source_id: r for r in recs}
        status = {}
        for sid in ids:
            r = by_sid.get(sid)
            status[sid] = {
                'imported': bool(r),
                'published': bool(r and r.product_tmpl_id and r.product_tmpl_id.is_published),
                'id': r.id if r else None,
            }
        return _json({'ok': True, 'status': status})

    @http.route('/dropship/ext/import', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    def ext_import(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({})
        p = self._payload()
        if not self._authed(p):
            return _json({'ok': False, 'error': 'bad key'}, status=401)
        ids = self._clean_ids(p.get('ids'))
        if not ids:
            return _json({'ok': False, 'error': 'no valid product ids'}, status=400)
        publish = bool(p.get('publish'))
        # hard cap per call so a runaway "import whole page" can't hammer the API.
        # NB: a corrupted '0' string param is truthy, so `x or 60` keeps '0' and
        # int('0')==0 would slice ids to [] → silent "Imported 0". Guard: any
        # non-positive / unparseable value falls back to the default 60.
        try:
            cap = int(self._icp().get_param('uellow_dropship.ext_max_per_call') or 60)
        except (TypeError, ValueError):
            cap = 60
        if cap <= 0:
            cap = 60
        ids = ids[:cap]
        _logger.info('EXT_IMPORT received ids=%s publish=%s', ids, publish)

        env = request.env
        svc = env['dropship.import.service'].sudo()
        try:
            svc.run_now({'source_ids': ids, 'skip_existing': False,
                         'enrich_on_import': True, 'mark_as_deal': False})
        except Exception as e:  # noqa: BLE001
            _logger.exception('ext import failed')
            return _json({'ok': False, 'error': str(e)[:200]}, status=500)

        DP = env['dropship.product'].sudo()
        recs = DP.search([('source_id', 'in', ids)])
        published = 0
        if publish and recs:
            try:
                recs.action_publish()
                published = len(recs)
            except Exception as e:  # noqa: BLE001
                _logger.warning('ext publish failed: %s', e)
        env.cr.commit()

        # classify anything that did NOT import so the popup shows a real reason
        # (blocked by the prohibited-terms filter vs. couldn't be fetched)
        got = set(recs.mapped('source_id'))
        skipped = []
        if len(got) < len(ids):
            prov = env['dropship.provider'].sudo().search(
                [('code', '=', 'aliexpress'), ('state', '=', 'connected')], limit=1)
            ad = prov._adapter() if prov else None
            svc2 = env['dropship.import.service'].sudo()
            for sid in ids:
                if sid in got:
                    continue
                reason = 'unknown'
                try:
                    u = ad.get_product(sid) if ad else None
                    if not u:
                        reason = 'not_found'
                    elif svc2._excluded(self._icp(), u):
                        reason = 'blocked'
                except Exception:  # noqa: BLE001
                    reason = 'fetch_failed'
                skipped.append({'source_id': sid, 'reason': reason})
        if skipped:
            _logger.warning('EXT_IMPORT skipped %s', skipped)
        _logger.info('EXT_IMPORT result imported=%d published=%d', len(recs), published)

        items = [{
            'source_id': r.source_id,
            'id': r.id,
            'title': (r.title_en or '')[:80],
            'published': bool(r.product_tmpl_id and r.product_tmpl_id.is_published),
        } for r in recs]
        return _json({'ok': True, 'imported': len(recs),
                      'published': published, 'items': items,
                      'skipped': skipped})

    @http.route('/dropship/ext/download', type='http', auth='user')
    def ext_download(self, **kw):
        """Zip the bundled chrome_extension folder on the fly so an admin can
        download the extension straight from the settings page."""
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'chrome_extension')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, files in os.walk(base):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, base))
        buf.seek(0)
        return request.make_response(buf.read(), headers=[
            ('Content-Type', 'application/zip'),
            ('Content-Disposition',
             'attachment; filename="uellow-importer-extension.zip"')])
