# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
from .throttle_middleware import _uellow_throttle_page


class ThrottlePreview(http.Controller):
    @http.route('/rate-limited-preview', type='http', auth='public',
                csrf=False, sitemap=False)
    def preview(self, **kw):
        return Response(_uellow_throttle_page(),
                        content_type='text/html; charset=utf-8')
