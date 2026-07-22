"""Reviews — /api/mobile/v2/reviews/*

Wires the mobile app to the `uellow.product.review` model (in
`uellow_reviews`). Submission supports image attachments — each photo
is written as an ir.attachment and linked through `photo_ids`.
"""
import base64

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    img_url, bilingual, decode_image_upload,
)


def _decode(b64):
    """Decode an uploaded review photo, verifying it is REAL image bytes
    within the size cap (via the shared decode_image_upload helper). Accepts
    a raw/data-URI base64 string OR a {"data": ...} dict. Returns clean raw
    bytes, or None to skip a blank / non-image / oversized upload — so a
    malicious client can't stash arbitrary public blobs through reviews."""
    if isinstance(b64, dict):
        b64 = b64.get('data') or b64.get('image') or b64.get('url') or ''
    if not b64:
        return None
    raw, err = decode_image_upload(b64)
    return raw if not err else None


def _attach_review_photos(review, photos):
    """photos = list of base64 strings → create ir.attachment rows and
    link them through `photo_ids`."""
    if not photos:
        return
    Attachment = request.env['ir.attachment'].sudo()
    new_ids = []
    for idx, b64 in enumerate(photos):
        raw = _decode(b64)
        if not raw:
            continue
        att = Attachment.create({
            'name': f'review-{review.id}-{idx + 1}.jpg',
            'datas': base64.b64encode(raw),
            'res_model': 'uellow.product.review',
            'res_id': review.id,
            'type': 'binary',
            'mimetype': 'image/jpeg',
            'public': True,
        })
        new_ids.append(att.id)
    if new_ids:
        review.write({'photo_ids': [(4, aid) for aid in new_ids]})



def _award_review_points(partner, has_photo):
    """v2.1.50 — loyalty points for a verified review. Reads the earn
    values from uellow.loyalty.program (points_review_text/photo) and
    credits the partner's LIVE loyalty.card. Returns the points granted
    (0 when the program/module is missing)."""
    try:
        Prog = request.env.get('uellow.loyalty.program')
        pts_text, pts_photo = 5, 15
        if Prog is not None:
            prog = Prog.sudo().search([], limit=1)
            if prog:
                pts_text = int(getattr(prog, 'points_review_text', 5) or 5)
                pts_photo = int(getattr(prog, 'points_review_photo', 15)
                                or 15)
        pts = pts_photo if has_photo else pts_text
        if pts <= 0:
            return 0
        Card = request.env['loyalty.card'].sudo()
        card = Card.search([
            ('partner_id', '=', partner.id),
            ('program_id.program_type', '=', 'loyalty'),
        ], limit=1)
        if not card:
            program = request.env['loyalty.program'].sudo().search(
                [('program_type', '=', 'loyalty')], limit=1)
            if not program:
                return 0
            card = Card.create({'partner_id': partner.id,
                                'program_id': program.id, 'points': 0})
        card.write({'points': card.points + pts})
        return pts
    except Exception:
        import logging
        logging.getLogger(__name__).exception('review points award failed')
        return 0


class MobileReviewsAPI(http.Controller):

    @http.route('/api/mobile/v2/reviews/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_review(self, **kw):
        p = get_payload()
        partner = current_partner()
        try:
            product_id = int(p.get('product_id') or 0)
            rating = int(round(float(p.get('rating') or 0)))
        except Exception:
            return fail('BAD_REQUEST', 'product_id and rating required')
        if not product_id or not (1 <= rating <= 5):
            return fail('BAD_REQUEST', 'rating must be 1..5')

        Review = request.env.get('uellow.product.review')
        if Review is None:
            return fail('UNAVAILABLE', 'Reviews module not installed', 503)

        body = (p.get('body') or p.get('message') or '').strip()
        title = (p.get('title') or '').strip()
        if not body:
            return fail('BAD_REQUEST', 'review body is required')

        existing = Review.sudo().search([
            ('product_id', '=', product_id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        vals = {
            'product_id': product_id,
            'partner_id': partner.id,
            'rating':     rating,
            'title':      title,
            'body':       body,
        }
        if existing:
            existing.write(vals)
            r = existing
        else:
            r = Review.sudo().create(vals)

        # Attach uploaded photos (base64). `photos` may be a list or a
        # JSON-encoded list — accept either.
        photos = p.get('photos') or p.get('images') or []
        if isinstance(photos, str):
            import json as _json
            try:
                photos = _json.loads(photos)
            except Exception:
                photos = []
        if isinstance(photos, list) and photos:
            _attach_review_photos(r, photos[:8])     # cap at 8 to be safe

        # v2.1.29 — ALSO sync into the native rating.rating record so the
        # review appears in the new Reviews module (product_reviews wraps
        # rating.rating) AND feeds product.rating_avg/rating_count.
        points_awarded = 0
        try:
            Rating = request.env['rating.rating'].sudo()
            IrModel = request.env['ir.model'].sudo()
            model_rec = IrModel.search(
                [('model', '=', 'product.template')], limit=1)
            ex = Rating.search([
                ('res_model', '=', 'product.template'),
                ('res_id', '=', product_id),
                ('partner_id', '=', partner.id),
            ], limit=1)
            rvals = {
                'res_model_id': model_rec.id,
                'res_id': product_id,
                'partner_id': partner.id,
                'rated_partner_id': partner.id,
                'rating': float(rating),
                'feedback': body,
                # v2.1.35 — reviews land PENDING: consumed=False keeps them
                # out of the app list + product stats until an admin clicks
                # Publish in the Reviews module (which sets consumed=True).
                'consumed': False,
            }
            if 'review_title' in Rating._fields:
                rvals['review_title'] = title
            if 'is_verified_purchase' in Rating._fields:
                # verified = the customer actually bought it
                bought = request.env['sale.order.line'].sudo().search_count([
                    ('order_id.partner_id', '=', partner.id),
                    ('order_id.state', 'in', ('sale', 'done')),
                    ('product_id.product_tmpl_id', '=', product_id),
                ]) > 0
                rvals['is_verified_purchase'] = bought
            rec = ex if ex else Rating.create(rvals)
            if ex:
                ex.write(rvals)
            # v2.1.50 — loyalty reward: first review of a product the
            # customer actually BOUGHT earns points (photo pays more).
            if not ex and rvals.get('is_verified_purchase'):
                points_awarded = _award_review_points(
                    partner, bool(isinstance(photos, list) and photos))
            # mirror the photos into rating.review.image
            if (isinstance(photos, list) and photos
                    and 'rating.review.image' in request.env):
                Img = request.env['rating.review.image'].sudo()
                for i, ph in enumerate(photos[:8]):
                    # Validate as real image bytes (magic-number + size cap)
                    # before mirroring — never store a raw/oversized/non-image
                    # blob just because the client sent one.
                    raw = _decode(ph)
                    if not raw:
                        continue
                    Img.create({'rating_id': rec.id, 'sequence': i,
                                'image': base64.b64encode(raw),
                                'name': 'review-%s-%s' % (rec.id, i)})
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'rating.rating sync failed for review %s', r.id)

        return ok({
            'id': r.id,
            'state': r.state,
            'pending_approval': r.state != 'approved',
            'points_awarded': points_awarded,
            'photo_urls': [
                img_url('ir.attachment', a.id, 'datas', unique=a.write_date)
                for a in r.photo_ids
            ],
        })

    @http.route('/api/mobile/v2/reviews/prompt', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def review_prompt(self, **kw):
        """v2.1.50 — post-delivery review nudge. Returns the most recent
        DELIVERED order (last 21 days) that still has unreviewed products
        for this customer, plus the loyalty reward amounts — or
        {'prompt': None} when there's nothing to ask about."""
        from datetime import datetime, timedelta
        partner = current_partner()
        Order = request.env['sale.order'].sudo()
        # v2.1.94 — explicit ?order_id= (the account-card "Rate" button):
        # prompt for THAT order, no 21-day window.
        try:
            req_oid = int(kw.get('order_id') or 0)
        except Exception:
            req_oid = 0
        if req_oid:
            orders = Order.search([
                ('id', '=', req_oid),
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
            ])
        else:
            orders = Order.search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
                ('date_order', '>=', datetime.now() - timedelta(days=21)),
            ], order='date_order desc', limit=10)
        delivered = orders.filtered(
            lambda o: getattr(o, 'delivery_status', '') == 'delivered')
        if not delivered:
            return ok({'prompt': None})
        Rating = request.env['rating.rating'].sudo()
        reviewed_ids = set(Rating.search([
            ('res_model', '=', 'product.template'),
            ('partner_id', '=', partner.id),
        ]).mapped('res_id'))
        # earn values for the message
        pts_text, pts_photo = 5, 15
        Prog = request.env.get('uellow.loyalty.program')
        if Prog is not None:
            prog = Prog.sudo().search([], limit=1)
            if prog:
                pts_text = int(getattr(prog, 'points_review_text', 5) or 5)
                pts_photo = int(getattr(prog, 'points_review_photo', 15)
                                or 15)
        for o in delivered:
            items = []
            for l in o.order_line:
                if l.display_type or getattr(l, 'is_reward_line', False):
                    continue
                tmpl = l.product_id.product_tmpl_id
                if not tmpl:
                    continue
                # v2.1.95 — explicit "Rate" tap: show ALL the order's
                # products (re-review allowed); the auto-prompt still
                # skips already-reviewed ones.
                if tmpl.id in reviewed_ids and not req_oid:
                    continue
                if any(it['product_id'] == tmpl.id for it in items):
                    continue
                items.append({
                    'product_id': tmpl.id,
                    'name': bilingual(tmpl, 'name'),
                    'image': img_url('product.template', tmpl.id,
                                     'image_256', unique=tmpl.write_date),
                })
            if items:
                return ok({'prompt': {
                    'order_id': o.id,
                    'order_name': o.name,
                    'items': items[:6],
                    'points_text': pts_text,
                    'points_photo': pts_photo,
                }})
        return ok({'prompt': None})

    @http.route('/api/mobile/v2/reviews/mine', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def my_reviews(self, **kw):
        partner = current_partner()
        Review = request.env.get('uellow.product.review')
        if Review is None:
            return ok([])
        reviews = Review.sudo().search([
            ('partner_id', '=', partner.id),
        ], order='create_date desc')
        return ok([{
            'id': r.id,
            'product_id': r.product_id.id,
            'product_name': bilingual(r.product_id, 'name'),
            'rating': int(r.rating or 0),
            'title': r.title or '',
            'body':  r.body or '',
            'state': r.state,
            'approved': r.state == 'approved',
            'date': r.create_date.isoformat() if r.create_date else None,
            'photo_urls': [
                img_url('ir.attachment', a.id, 'datas', unique=a.write_date)
                for a in r.photo_ids
            ],
        } for r in reviews])
