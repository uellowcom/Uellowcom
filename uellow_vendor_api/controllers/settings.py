# -*- coding: utf-8 -*-
"""Vendor settings — /api/vendor/v1/settings*"""
import base64
import binascii

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor,
)
from .auth import _serialize_vendor


class VendorSettingsAPI(http.Controller):

    @http.route('/api/vendor/v1/settings/profile', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_profile(self, **kw):
        v = current_vendor()
        p = get_payload()
        vals = {}
        for f in ('store_name_en', 'store_name_ar', 'store_tagline_en',
                  'store_tagline_ar', 'store_description_en',
                  'store_description_ar', 'brand_color',
                  'business_name', 'commercial_reg',
                  'contact_phone', 'contact_email',
                  'bank_iban', 'bank_name'):
            if f in p:
                vals[f] = p[f]
        if p.get('logo_base64'):
            try:
                raw = base64.b64decode(p['logo_base64'].split(',', 1)[-1])
                vals['logo_image'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        if p.get('banner_base64'):
            try:
                raw = base64.b64decode(p['banner_base64'].split(',', 1)[-1])
                vals['banner_image'] = base64.b64encode(raw)
            except (binascii.Error, ValueError):
                pass
        if vals:
            v.sudo().write(vals)
        return ok({'vendor': _serialize_vendor(v)})

    @http.route('/api/vendor/v1/app/languages', type='http', auth='public',
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
            out.append({'code': l.code, 'name': l.name, 'flag': flag,
                        'direction': l.direction or 'ltr'})
        return ok(out)
