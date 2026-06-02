# -*- coding: utf-8 -*-
"""Vendor reviews — /api/vendor/v1/reviews*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, img_url,
)


def _try_review_model():
    """Find whichever review model is installed in this DB."""
    env = request.env
    for m in ('uellow.product.review', 'product.review', 'mobile.review'):
        if m in env:
            return env[m].sudo()
    return None


class VendorReviewsAPI(http.Controller):

    @http.route('/api/vendor/v1/reviews', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_reviews(self, **kw):
        v = current_vendor()
        Review = _try_review_model()
        if Review is None:
            return ok([])
        p = get_payload()
        try:
            page = max(1, int(p.get('page') or 1))
            per_page = min(50, max(5, int(p.get('per_page') or 20)))
        except (TypeError, ValueError):
            page, per_page = 1, 20
        # All reviews on this vendor's products
        Tmpl = request.env['product.template'].sudo()
        vendor_product_ids = Tmpl.search([('vendor_id', '=', v.id)]).ids
        domain = []
        # try common field names
        for fname in ('product_tmpl_id', 'product_id', 'template_id'):
            if fname in Review._fields:
                domain = [(fname, 'in', vendor_product_ids)]
                break
        total = Review.search_count(domain) if domain else 0
        rows = Review.search(domain, order='id desc',
                             limit=per_page, offset=(page-1)*per_page) if domain else Review.browse()
        out = []
        for r in rows:
            rating = float(getattr(r, 'rating', 0) or getattr(r, 'stars', 0) or 0)
            comment = getattr(r, 'comment', '') or getattr(r, 'review', '') or getattr(r, 'body', '')
            author = getattr(r, 'partner_id', None) or getattr(r, 'author_id', None)
            reply = getattr(r, 'vendor_reply', '') or getattr(r, 'reply', '') or ''
            product = None
            for fname in ('product_tmpl_id', 'product_id', 'template_id'):
                if fname in r._fields:
                    product = r[fname]
                    break
            out.append({
                'id': r.id,
                'rating': rating,
                'comment': comment,
                'reply': reply,
                'when': (r.create_date.isoformat() if r.create_date else ''),
                'author': {
                    'name': (author.name if author else ''),
                    'avatar_url': img_url('res.partner', author.id, 'image_128',
                                           unique=author.write_date)
                                   if author and getattr(author, 'image_128', None) else None,
                } if author else None,
                'product': {
                    'id': product.id if product else 0,
                    'name': product.name if product else '',
                } if product else None,
            })
        return ok(out, meta={
            'page': page, 'per_page': per_page, 'total': total,
            'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/vendor/v1/reviews/<int:rid>/reply', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def reply(self, rid, **kw):
        Review = _try_review_model()
        if Review is None:
            return fail('NO_REVIEW_MODEL', 'No review model installed', 404)
        p = get_payload()
        text = (p.get('reply') or '').strip()
        if not text:
            return fail('EMPTY', 'reply text required')
        r = Review.browse(rid)
        if not r.exists():
            return fail('NOT_FOUND', 'Review not found', 404)
        # Try common field names
        for fname in ('vendor_reply', 'reply'):
            if fname in r._fields:
                r.sudo().write({fname: text})
                return ok({'replied': True})
        return fail('NO_REPLY_FIELD', 'Review model has no reply field')
