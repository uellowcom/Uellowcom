# -*- coding: utf-8 -*-
"""Serve the in-browser builder HTML at /uellow-builder.

The HTML is a single file that loads pages/themes/navbar from the admin
API via fetch. Users must be authenticated as internal (group_user).
"""
import os

from odoo import http
from odoo.http import request
from odoo.modules import get_module_path


class BuilderView(http.Controller):

    @http.route('/uellow-builder', type='http', auth='user',
                methods=['GET'], csrf=False)
    def builder(self, **kw):
        if not request.env.user.has_group('base.group_user'):
            return request.redirect('/web/login?redirect=/uellow-builder')
        path = os.path.join(get_module_path('uellow_mobile_pages'),
                            'static', 'builder', 'index.html')
        try:
            with open(path, 'rb') as f:
                body = f.read()
        except FileNotFoundError:
            return request.not_found()
        return request.make_response(body, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])
