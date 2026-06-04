"""Reviews — /api/mobile/v2/reviews/*

Wires the mobile app to the `uellow.product.review` model (in
`uellow_reviews`). Submission supports image attachments — each photo
is written as an ir.attachment and linked through `photo_ids`.
"""
import base64
import binascii

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    img_url, bilingual,
)


def _decode(b64):
    """Strip a possible 'data:image/...;base64,' prefix and decode."""
    if not b64:
        return None
    s = b64.strip()
    if s.startswith('data:'):
        s = s.split(',', 1)[-1]
    try:
        return base64.b64decode(s)
    except (binascii.Error, ValueError):
        return None


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
                'consumed': True,
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
            # mirror the photos into rating.review.image
            if (isinstance(photos, list) and photos
                    and 'rating.review.image' in request.env):
                Img = request.env['rating.review.image'].sudo()
                for i, ph in enumerate(photos[:8]):
                    data = ph.get('data') if isinstance(ph, dict) else ph
                    if not data:
                        continue
                    if isinstance(data, str) and ',' in data[:64]:
                        data = data.split(',', 1)[1]
                    Img.create({'rating_id': rec.id, 'sequence': i,
                                'image': data,
                                'name': 'review-%s-%s' % (rec.id, i)})
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                'rating.rating sync failed for review %s', r.id)

        return ok({
            'id': r.id,
            'state': r.state,
            'pending_approval': r.state != 'approved',
            'photo_urls': [
                img_url('ir.attachment', a.id, 'datas', unique=a.write_date)
                for a in r.photo_ids
            ],
        })

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
