# -*- coding: utf-8 -*-
"""Serve the Google Merchant feeds (Arabic + English). Normally rebuilt in the
background by a cron; if a file is missing (e.g. right after a container
recreate) the first hit rebuilds that language once, guarded by a lock."""
import os

from odoo import http
from odoo.http import request

from ..models.gmc_feed import GMC_DIR, GMC_FILES


class GmcFeedController(http.Controller):

    def _serve(self, lang):
        path = GMC_FILES[lang]
        if not os.path.exists(path):
            lock = GMC_DIR + '/.building-' + lang
            try:
                os.makedirs(GMC_DIR, exist_ok=True)
                if os.path.exists(lock):
                    return request.make_response(
                        'Feed is being generated, please retry shortly.',
                        status=503, headers=[('Retry-After', '60')])
                open(lock, 'w').close()
                try:
                    request.env['product.template'].sudo()._uc_build_gmc_feed(lang)
                finally:
                    try:
                        os.remove(lock)
                    except Exception:
                        pass
            except Exception:
                return request.make_response(
                    'Feed temporarily unavailable.', status=503,
                    headers=[('Retry-After', '120')])
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except Exception:
            return request.make_response(
                'Feed temporarily unavailable.', status=503,
                headers=[('Retry-After', '120')])
        return request.make_response(data, headers=[
            ('Content-Type', 'application/xml; charset=utf-8'),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    @http.route(['/google-merchant.xml', '/google-merchant-ar.xml'],
                type='http', auth='public', csrf=False, sitemap=False)
    def google_merchant_feed_ar(self, **kw):
        return self._serve('ar_001')

    @http.route('/google-merchant-en.xml', type='http', auth='public',
                csrf=False, sitemap=False)
    def google_merchant_feed_en(self, **kw):
        return self._serve('en_US')
