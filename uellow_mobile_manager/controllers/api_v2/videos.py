"""TikTok-style vertical video feed + social layer for the Reels tab.

Endpoints:
  GET  /api/mobile/v2/videos/feed?cursor=&limit=
  GET  /api/mobile/v2/videos/search?q=&limit=        — grid search by product name
  GET  /api/mobile/v2/videos/<id>/comments           — list comments
  POST /api/mobile/v2/videos/<id>/comments           — add a comment (auth)
  POST /api/mobile/v2/videos/<id>/share              — bump the share counter

Each feed/search item carries engagement stats (views / wishlist / shares /
comments) + `is_wishlisted` for the current user, so the Reels UI can show the
counter row and a filled red heart.
"""
import json
import random

from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, fail, get_lang, current_partner, require_auth
from .products import (
    serialize_product_card,
    _serialize_product_videos,
    _domain_published_for_app,
)


def _is_wishlisted(partner, tmpl):
    if not partner or not tmpl:
        return False
    Wish = request.env.get('mobile.wishlist')
    if Wish is None:
        return False
    try:
        # Match exactly how add/remove store it: any variant of the template.
        variant_ids = tmpl.product_variant_ids.ids
        if not variant_ids:
            return False
        return bool(Wish.sudo().search_count([
            ('partner_id', '=', partner.id),
            ('product_id', 'in', variant_ids)]))
    except Exception:
        return False


def _video_stats(vrec, tmpl):
    """Engagement counters for one product.video record."""
    views = 0
    shares = 0
    comments = 0
    wishlist = 0
    if vrec is not None:
        views = int(getattr(vrec, 'bunny_views', 0) or 0)
        shares = int(getattr(vrec, 'share_count', 0) or 0)
        try:
            comments = int(getattr(vrec, 'comment_count', 0) or 0)
        except Exception:
            comments = 0
        try:
            wishlist = int(getattr(vrec, 'wishlist_count', 0) or 0)
        except Exception:
            wishlist = 0
    return {'views': views, 'shares': shares,
            'comments': comments, 'wishlist': wishlist}


def _oos_blocked(p):
    """True when the product is out of stock AND not allowed to continue
    selling — such products are hidden from the Reels feed/search."""
    # "Continue selling when out of stock" → always show.
    if getattr(p, 'allow_out_of_stock_order', True):
        return False
    # Only stockable products can be out of stock.
    storable = getattr(p, 'is_storable', None)
    if storable is None:
        storable = (getattr(p, 'type', '') == 'product')
    if not storable:
        return False
    try:
        qty = p.virtual_available
    except Exception:
        try:
            qty = p.qty_available
        except Exception:
            qty = 0
    return (qty or 0) <= 0


def _build_video_item(p, lang, partner):
    """Full Reels slide for one product (or None if no playable video)."""
    if _oos_blocked(p):
        return None
    videos = _serialize_product_videos(p)
    playable = [v for v in videos
                if (v.get('file_url') or v.get('embed_url')
                    or v.get('tiktok_url') or v.get('video_url'))]
    if not playable:
        return None
    card = serialize_product_card(p, lang)
    if not card:
        return None
    vid = playable[0]
    vrec = None
    try:
        if vid.get('id'):
            vrec = request.env['product.video'].sudo().browse(int(vid['id']))
            if not vrec.exists():
                vrec = None
    except Exception:
        vrec = None
    return {
        'product': card,
        'video': vid,
        'video_count': len(playable),
        'stats': _video_stats(vrec, p),
        'is_wishlisted': _is_wishlisted(partner, p),
    }


def _comment_json(c, with_replies=False):
    d = {
        'id': c.id,
        'author': c.display_author(),
        'body': c.body or '',
        'likes': c.likes or 0,
        'is_seller': bool(c.is_seller),
        'parent_id': c.parent_id.id if c.parent_id else None,
        'created': c.create_date.isoformat() if c.create_date else '',
    }
    if with_replies:
        d['replies'] = [_comment_json(r)
                        for r in c.reply_ids.filtered('active')
                        .sorted(key=lambda x: x.create_date or x.id)]
    return d


class MobileVideosAPI(http.Controller):

    @http.route('/api/mobile/v2/videos/feed', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def videos_feed(self, **kw):
        lang = get_lang()
        partner = current_partner()
        try:
            cursor = int(kw.get('cursor') or 0)
        except Exception:
            cursor = 0
        try:
            limit = max(1, min(30, int(kw.get('limit') or 10)))
        except Exception:
            limit = 10

        Tmpl = request.env['product.template'].sudo()
        # Random-order mode: when the app passes a per-open `seed`, the whole
        # video-bearing catalogue is deterministically shuffled by that seed
        # and paginated by offset (the `cursor` param doubles as the offset).
        # A fresh seed on each tab-open => a different order every time.
        seed = kw.get('seed')
        try:
            seed = int(seed) if seed not in (None, '') else None
        except Exception:
            seed = None

        if seed is not None:
            base = _domain_published_for_app(include_oos=True)
            if 'has_product_video' in Tmpl._fields:
                base.append(('has_product_video', '=', True))
            all_ids = Tmpl.search(base).ids
            random.Random(seed).shuffle(all_ids)
            offset = cursor if cursor > 0 else 0
            window = all_ids[offset:offset + limit * 4]
            items = []
            consumed = 0
            for p in Tmpl.browse(window):
                consumed += 1
                item = _build_video_item(p, lang, partner)
                if not item:
                    continue
                items.append(item)
                if len(items) >= limit:
                    break
            new_off = offset + consumed
            return ok({'items': items, 'cursor': new_off,
                       'has_more': new_off < len(all_ids)})

        domain = _domain_published_for_app(include_oos=True)
        if cursor > 0:
            domain.append(('id', '<', cursor))
        if 'has_product_video' in Tmpl._fields:
            domain.append(('has_product_video', '=', True))

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
            item = _build_video_item(p, lang, partner)
            if not item:
                continue
            items.append(item)
            last_id = p.id
            if len(items) >= limit:
                break

        return ok({'items': items, 'cursor': last_id,
                   'has_more': len(items) >= limit})

    @http.route('/api/mobile/v2/videos/search', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def videos_search(self, **kw):
        """Grid search: products matching `q` by name that have a video."""
        lang = get_lang()
        partner = current_partner()
        q = (kw.get('q') or '').strip()
        try:
            limit = max(1, min(60, int(kw.get('limit') or 40)))
        except Exception:
            limit = 40
        if not q:
            return ok({'items': []})
        Tmpl = request.env['product.template'].sudo()
        domain = _domain_published_for_app(include_oos=True)
        domain += ['|', ('name', 'ilike', q), ('default_code', 'ilike', q)]
        if 'has_product_video' in Tmpl._fields:
            domain.append(('has_product_video', '=', True))
        candidates = Tmpl.search(domain, limit=limit * 3)
        items = []
        for p in candidates:
            item = _build_video_item(p, lang, partner)
            if item:
                items.append(item)
            if len(items) >= limit:
                break
        return ok({'items': items, 'query': q})

    @http.route('/api/mobile/v2/videos/<int:vid>/comments', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def video_comments(self, vid, **kw):
        Comment = request.env.get('product.video.comment')
        if Comment is None:
            return ok({'items': []})
        try:
            limit = max(1, min(100, int(kw.get('limit') or 50)))
        except Exception:
            limit = 50
        tops = Comment.sudo().search(
            [('video_id', '=', vid), ('active', '=', True),
             ('parent_id', '=', False)], limit=limit)
        return ok({'items': [_comment_json(c, with_replies=True) for c in tops],
                   'count': Comment.sudo().search_count(
                       [('video_id', '=', vid), ('active', '=', True)])})

    @http.route('/api/mobile/v2/videos/<int:vid>/comments', type='http',
                auth='public', methods=['POST'], csrf=False)
    @safe_endpoint
    @require_auth
    def video_comment_add(self, vid, **kw):
        Comment = request.env.get('product.video.comment')
        if Comment is None:
            return fail('NOT_SUPPORTED', 'Comments not available', 400)
        try:
            data = json.loads(request.httprequest.get_data() or b'{}')
        except Exception:
            data = {}
        body = (data.get('body') or kw.get('body') or '').strip()
        if not body:
            return fail('EMPTY', 'Comment text is required', 400)
        partner = current_partner()
        video = request.env['product.video'].sudo().browse(vid)
        if not video.exists():
            return fail('NOT_FOUND', 'Video not found', 404)
        vals = {
            'video_id': vid,
            'partner_id': partner.id if partner else False,
            'author_name': partner.name if partner else 'Guest',
            'body': body[:2000],
        }
        # Optional reply target.
        parent = data.get('parent_id') or kw.get('parent_id')
        if parent:
            try:
                pc = Comment.sudo().browse(int(parent))
                if pc.exists() and pc.video_id.id == vid and not pc.parent_id:
                    vals['parent_id'] = pc.id
            except Exception:
                pass
        c = Comment.sudo().create(vals)
        return ok(_comment_json(c))

    @http.route('/api/mobile/v2/videos/<int:vid>/share', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def video_share(self, vid, **kw):
        video = request.env['product.video'].sudo().browse(vid)
        if not video.exists():
            return fail('NOT_FOUND', 'Video not found', 404)
        try:
            video.share_count = (video.share_count or 0) + 1
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'shares': video.share_count or 0})
