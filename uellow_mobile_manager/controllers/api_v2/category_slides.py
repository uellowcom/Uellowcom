# -*- coding: utf-8 -*-
"""
Category header slides (v2.1.56)
================================
GET /api/mobile/v2/category/<id>/slides       — slide list for the shop
                                                page header slider
GET /api/mobile/v2/category-slide/<id>/image  — slide image binary
"""
import base64

from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, get_website


class MobileCategorySlidesAPI(http.Controller):

    @http.route('/api/mobile/v2/category/<int:cid>/slides', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def category_slides(self, cid, **kw):
        wid = None
        try:
            wid = get_website().id
        except Exception:
            pass
        dom = [('category_id', '=', cid), ('active', '=', True)]
        if wid:
            dom = ['|', ('website_id', '=', False),
                   ('website_id', '=', wid)] + dom
        slides = request.env['mobile.category.slide'].sudo().search(dom)
        return ok({'slides': [s.to_public_dict() for s in slides]})

    @http.route('/api/mobile/v2/category-slide/<int:sid>/image',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    def slide_image(self, sid, **kw):
        s = request.env['mobile.category.slide'].sudo().browse(sid)
        if not s.exists() or not s.image:
            return request.not_found()
        data = base64.b64decode(s.image)
        mime = 'image/png'
        if data[:3] == b'GIF':
            mime = 'image/gif'
        elif data[:2] == b'\xff\xd8':
            mime = 'image/jpeg'
        elif data[:4] == b'RIFF':
            mime = 'image/webp'
        return request.make_response(data, headers=[
            ('Content-Type', mime),
            ('Content-Length', str(len(data))),
            ('Cache-Control', 'public, max-age=600'),
        ])
