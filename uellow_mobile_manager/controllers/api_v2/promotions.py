# -*- coding: utf-8 -*-
"""
Promotions — public assets (v2.1.39)
====================================
GET /api/mobile/v2/promotions/<id>/icon — banner icon binary (public:
guests lack read ACL on mobile.app.promotion, so /web/image 403s).
"""
import base64

from odoo import http
from odoo.http import request


class MobilePromotionsAPI(http.Controller):

    @http.route('/api/mobile/v2/promotions/<int:promo_id>/icon',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    def promo_icon(self, promo_id, **kw):
        Promo = request.env.get('mobile.app.promotion')
        if Promo is None:
            return request.not_found()
        p = Promo.sudo().browse(promo_id)
        if not p.exists() or not p.banner_icon:
            return request.not_found()
        data = base64.b64decode(p.banner_icon)
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
            ('Cache-Control', 'public, max-age=3600'),
        ])
