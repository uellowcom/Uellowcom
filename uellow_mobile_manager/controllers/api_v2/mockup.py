"""Static mockup previews — driver app + home page builder."""
import os
from odoo import http
from odoo.modules import get_module_path


def _serve_mockup(rel_parts):
    path = os.path.join(get_module_path('uellow_mobile_manager'),
                        'static', 'mockups', *rel_parts)
    try:
        with open(path, 'rb') as f:
            body = f.read()
    except FileNotFoundError:
        return http.request.not_found()
    return http.request.make_response(
        body, headers=[('Content-Type', 'text/html; charset=utf-8'),
                       ('Cache-Control', 'no-store')])


class Mockups(http.Controller):

    @http.route('/driver-mockup', type='http', auth='public',
                methods=['GET'], csrf=False)
    def driver_mockup(self, **kw):
        return _serve_mockup(('driver-app', 'index.html'))

    @http.route('/home-builder-mockup', type='http', auth='public',
                methods=['GET'], csrf=False)
    def home_builder_mockup(self, **kw):
        return _serve_mockup(('home-builder', 'index.html'))
