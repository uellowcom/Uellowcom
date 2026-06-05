"""Public image proxy — /api/mobile/v2/img/<model>/<id>/<field>

Lets the mobile app read images on whitelisted models without needing
public ACL on each model individually. Returns the raw image bytes with
strong caching headers. The whitelist prevents using this as a generic
file-read endpoint.
"""
import base64
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


# Models the app is allowed to fetch images for. (model, field)
_WHITELIST = {
    ('mobile.slider',           'image'),
    ('mobile.category.icon',    'icon_image'),
    ('mobile.popup',            'image'),
    ('mobile.section',          'banner_image'),
    # product images already work via /web/image because website ACLs grant
    # public read on product.template/product.product. Listed here too so
    # the same proxy URL works for everything.
    ('product.template',        'image_1024'),
    ('product.template',        'image_512'),
    ('product.template',        'image_256'),
    ('product.template',        'image_128'),
    ('product.product',         'image_1024'),
    ('product.product',         'image_512'),
    ('product.product',         'image_256'),
    ('product.product',         'image_128'),
    ('product.public.category', 'image'),
    ('product.public.category', 'image_1024'),
    ('product.public.category', 'image_512'),
    ('product.image',           'image_1024'),
    ('product.image',           'image_512'),
    ('product.attribute.value', 'image'),
    ('product.brand',           'image_1024'),
    ('product.brand',           'image_512'),
    ('product.brand',           'image_128'),
    ('res.partner',             'image_128'),
    ('res.partner',             'image_256'),
    ('uellow.vendor',           'logo_image'),
    ('uellow.vendor',           'banner_image'),
}


class MobileImageProxy(http.Controller):

    @http.route([
        '/api/mobile/v2/img/<string:model>/<int:rec_id>/<string:field>',
        '/api/mobile/v2/img/<string:model>/<int:rec_id>/<string:field>/<string:unique>',
    ], type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    def fetch_image(self, model, rec_id, field, unique=None, **kw):
        if (model, field) not in _WHITELIST:
            return Response('Forbidden', status=403)
        try:
            rec = request.env[model].sudo().browse(rec_id)
            if not rec.exists():
                return Response('Not found', status=404)
            raw = getattr(rec, field, False)
            if not raw:
                return Response('No image', status=404)
            data = base64.b64decode(raw) if isinstance(raw, (str, bytes)) and not isinstance(raw, (bytearray,)) \
                   else bytes(raw)
        except Exception as e:
            _logger.warning('image proxy %s/%s/%s: %s', model, rec_id, field, e)
            return Response('Error', status=500)

        # Detect MIME from magic bytes
        mime = 'image/png'
        if data[:3] == b'\xff\xd8\xff':
            mime = 'image/jpeg'
        elif data[:6] in (b'GIF87a', b'GIF89a'):
            mime = 'image/gif'
        elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            mime = 'image/webp'

        headers = [
            ('Content-Type',  mime),
            ('Cache-Control', 'public, max-age=86400, immutable'),
            ('Access-Control-Allow-Origin', '*'),
        ]
        return Response(data, headers=headers)
