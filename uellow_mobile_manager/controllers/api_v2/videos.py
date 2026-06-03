"""TikTok-style vertical video feed for the mobile app's Reels tab.

Endpoint: GET /api/mobile/v2/videos/feed?cursor=...&limit=10

Returns products that have at least one playable video, paginated via a
cursor (last seen product id). Each entry includes everything the Reels
UI needs to render a full slide: product card + first video URL +
thumbnail + cart/wishlist hints.

Algorithm: trending-first (sales_count desc when available), then newest,
then a deterministic shuffle on the rest. Products without a usable
video are dropped server-side so the client doesn't have to filter.
"""
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, get_lang
from .products import (
    serialize_product_card,
    _serialize_product_videos,
    _domain_published_for_app,
)


class MobileVideosAPI(http.Controller):

    @http.route('/api/mobile/v2/videos/feed', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def videos_feed(self, **kw):
        lang = get_lang()
        try:
            cursor = int(kw.get('cursor') or 0)
        except Exception:
            cursor = 0
        try:
            limit = max(1, min(30, int(kw.get('limit') or 10)))
        except Exception:
            limit = 10

        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app(include_oos=True)
        # Optional cursor — pull templates whose id is less than the cursor
        # to avoid showing the same slides as before.
        if cursor > 0:
            domain.append(('id', '<', cursor))
        # Optional: only video-bearing products. The cheap filter is to
        # look at the `has_product_video` cached flag if it exists,
        # otherwise scan-and-filter Python-side.
        if 'has_product_video' in Tmpl._fields:
            domain.append(('has_product_video', '=', True))

        # Pull a bigger batch (3x limit) since some may have no videos
        # serializable for the app even when has_product_video is True.
        order = 'sales_count desc, write_date desc' \
            if 'sales_count' in Tmpl._fields else 'write_date desc'
        try:
            candidates = Tmpl.search(domain, order=order, limit=limit * 4)
        except Exception:
            candidates = Tmpl.search(_domain_published_for_app(include_oos=True),
                                     order='write_date desc', limit=limit * 4)

        items = []
        last_id = cursor
        for p in candidates:
            videos = _serialize_product_videos(p)
            # Need at least one playable URL (file, embed, or tiktok)
            playable = [v for v in videos
                        if (v.get('file_url') or v.get('embed_url')
                            or v.get('tiktok_url') or v.get('video_url'))]
            if not playable:
                continue
            card = serialize_product_card(p, lang)
            if not card:
                continue
            items.append({
                'product': card,
                'video': playable[0],   # first usable video
                'video_count': len(playable),
            })
            last_id = p.id
            if len(items) >= limit:
                break

        return ok({
            'items': items,
            'cursor': last_id,
            'has_more': len(items) >= limit,
        })
