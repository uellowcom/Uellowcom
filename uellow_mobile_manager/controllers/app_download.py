# -*- coding: utf-8 -*-
"""APK download endpoint. Serves the built Flutter APK with correct
mime type and a sensible filename. Lives separately so the file can be
swapped without touching other controllers."""
import os
from odoo import http
from odoo.http import request

_APK_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'static', 'downloads', 'uellow-v2.apk',
)


class UellowAppDownload(http.Controller):

    @http.route(['/download/uellow-app',
                 '/download/uellow.apk'],
                type='http', auth='public', csrf=False, methods=['GET', 'HEAD'])
    def download_apk(self, **kw):
        path = os.path.abspath(_APK_PATH)
        if not os.path.exists(path):
            return request.not_found()
        with open(path, 'rb') as f:
            data = f.read()
        return request.make_response(data, headers=[
            ('Content-Type', 'application/vnd.android.package-archive'),
            ('Content-Disposition', 'attachment; filename="uellow-v2.apk"'),
            ('Content-Length', str(len(data))),
            ('Cache-Control', 'no-store'),
        ])
