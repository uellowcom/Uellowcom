# -*- coding: utf-8 -*-
import re
from odoo import http
from odoo.http import request


class UellowTikTokVideoController(http.Controller):

    @http.route('/uellow/product/video/<int:product_tmpl_id>', type='json', auth='public', methods=['POST'], csrf=False)
    def get_product_videos(self, product_tmpl_id, **kwargs):
        """Return all active videos for a product template."""
        product = request.env['product.template'].sudo().browse(product_tmpl_id)
        if not product.exists():
            return {'videos': [], 'error': 'Product not found'}

        videos = product.product_video_ids.filtered(lambda v: v.active)
        return {
            'videos': [v.get_video_data() for v in videos],
            'has_video': bool(videos),
        }

    @http.route('/uellow/product/video/resolve-tiktok', type='json', auth='public', methods=['POST'], csrf=False)
    def resolve_tiktok_short_url(self, url='', **kwargs):
        """Try to resolve a TikTok short URL to extract the video ID."""
        try:
            import urllib.request
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            with urllib.request.urlopen(req, timeout=5) as resp:
                final_url = resp.url
            match = re.search(r'tiktok\.com/@[\w.]+/video/(\d+)', final_url)
            if match:
                return {'video_id': match.group(1), 'url': final_url}
        except Exception:
            pass
        return {'video_id': None, 'url': url}
