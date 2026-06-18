# -*- coding: utf-8 -*-
"""Vendor live commerce — shoppable product videos hosted on Bunny Stream.

Reuses the production product.video model + its Bunny upload helper
(_bunny_upload_one). A vendor records a clip in the app, it is uploaded to
Bunny, transcoded, and played (HLS) on the product everywhere."""
import base64
import binascii

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor,
)


def _ser_video(vid):
    return {
        'id': vid.id,
        'title': vid.name or '',
        'product_id': vid.product_tmpl_id.id if vid.product_tmpl_id else 0,
        'product': vid.product_tmpl_id.name if vid.product_tmpl_id else '',
        'type': vid.video_type or '',
        'guid': getattr(vid, 'bunny_video_id', '') or '',
        'playback_url': getattr(vid, 'bunny_playback_url', '') or '',
        'thumb_url': getattr(vid, 'bunny_thumb_url', '') or '',
        'status': getattr(vid, 'bunny_status', '') or '',
        'encode_pct': getattr(vid, 'bunny_encode_progress', 0) or 0,
        'views': getattr(vid, 'bunny_views', 0) or 0,
        'duration': getattr(vid, 'bunny_length_human', '') or '',
        'active': vid.active,
    }


class VendorVideosController(http.Controller):

    def _videos_domain(self, v):
        return [('product_tmpl_id.vendor_id', '=', v.id)]

    @http.route('/api/vendor/v1/videos', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_videos(self, **kw):
        v = current_vendor()
        vids = request.env['product.video'].sudo().with_context(active_test=False).search(
            self._videos_domain(v), order='sequence,id')
        return ok([_ser_video(x) for x in vids])

    @http.route('/api/vendor/v1/videos/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_video(self, **kw):
        v = current_vendor()
        if not v.cap('live'):
            return fail('FORBIDDEN', 'Shoppable video is disabled for your account.',
                        403, capability='live')
        p = get_payload()
        try:
            pid = int(p.get('product_id'))
        except (TypeError, ValueError):
            return fail('BAD_PRODUCT', 'product_id required')
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        b64 = p.get('video_base64') or ''
        if not b64:
            return fail('NO_VIDEO', 'video_base64 required')
        try:
            raw = base64.b64decode(b64.split(',', 1)[-1])
        except (binascii.Error, ValueError):
            return fail('BAD_VIDEO', 'video_base64 is not valid base64')
        if len(raw) > 80 * 1024 * 1024:
            return fail('TOO_LARGE', 'Video exceeds 80 MB limit')

        Video = request.env['product.video'].sudo()
        title = (p.get('title') or t.name or 'Product video')[:200]
        vid = Video.create({
            'name': title,
            'product_tmpl_id': t.id,
            'video_type': 'direct_upload',
            'video_file': base64.b64encode(raw),
            'video_filename': (p.get('filename') or 'clip.mp4'),
            'video_mimetype': 'video/mp4',
        })
        # Push to Bunny Stream (reuses the proven admin upload path).
        try:
            api_key, lib = vid._bunny_config()
            vid._bunny_upload_one(api_key, lib)
        except Exception as e:
            # keep the local record so the vendor can retry; report the reason
            return ok({**_ser_video(vid), 'upload_error': str(e)[:200]})
        return ok(_ser_video(vid))

    @http.route('/api/vendor/v1/videos/<int:vid_id>/delete', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_video(self, vid_id, **kw):
        v = current_vendor()
        vid = request.env['product.video'].sudo().with_context(active_test=False).browse(vid_id)
        if not vid.exists() or vid.product_tmpl_id.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Video not found', 404)
        vid.unlink()
        return ok({'id': vid_id, 'deleted': True})
