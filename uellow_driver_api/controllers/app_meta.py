# -*- coding: utf-8 -*-
"""App-level meta — /api/driver/v1/app/*"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok


class DriverAppMetaAPI(http.Controller):

    @http.route('/api/driver/v1/app/languages', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def languages(self, **kw):
        langs = request.env['res.lang'].sudo().search([('active', '=', True)])
        out = []
        for l in langs:
            flag = '🌐'
            parts = (l.code or '').split('_')
            if len(parts) > 1 and len(parts[1]) == 2 and parts[1].isalpha():
                cc = parts[1].upper()
                flag = ''.join(chr(127397 + ord(ch)) for ch in cc)
            if (l.code or '').startswith('ar'):
                flag = '🇰🇼'
            out.append({
                'code': l.code,
                'name': l.name,
                'iso':  l.iso_code or l.code,
                'direction': l.direction or 'ltr',
                'flag': flag,
            })
        return ok(out)

    @http.route('/api/driver/v1/app/version', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def version(self, **kw):
        return ok({
            'current': '1.0.0',
            'min_supported': '1.0.0',
            'latest': '1.0.0',
            'force_update': False,
        })
