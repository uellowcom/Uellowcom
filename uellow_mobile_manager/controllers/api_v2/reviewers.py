# -*- coding: utf-8 -*-
"""
Specialist reviewers (uellow_reviewers) — mobile API (v2.1.31)
==============================================================
GET  /products/<id>/expert-reviews → latest completed expert verdicts
GET  /reviewers/online             → approved online specialists
POST /reviewers/request            → ask a specialist (auth)
"""
from odoo import http
from odoo.http import request

from ._common import (safe_endpoint, get_payload, ok, fail, img_url,
                      current_partner, require_auth)

VERDICT_LABEL = {
    'recommend': {'en': 'Recommends buying', 'ar': 'أنصح بالشراء'},
    'not_recommend': {'en': 'Does not recommend', 'ar': 'لا أنصح'},
    'neutral': {'en': 'Neutral', 'ar': 'محايد'},
}


def _reviewer_json(rv):
    return {
        'id': rv.id,
        'name': rv.display_name or '',
        'avatar': img_url('reviewer.profile', rv.id, 'avatar',
                          unique=rv.write_date) if rv.avatar else None,
        'specialty': rv.specialty_text or '',
        'level': rv.level or '',
        'verified': bool(rv.verified),
        'online': bool(rv.is_online),
        'rating': round(float(rv.rating or 0), 1),
        'review_count': int(rv.review_count or 0),
        'price_written': float(rv.price_written or 0),
        'price_chat': float(rv.price_chat or 0),
        'allow_written': bool(rv.allow_written),
        'allow_chat': bool(rv.allow_chat),
    }


class MobileReviewersAPI(http.Controller):

    @http.route('/api/mobile/v2/products/<int:product_id>/expert-reviews',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def expert_reviews(self, product_id, **kw):
        Req = request.env.get('review.request')
        Prof = request.env.get('reviewer.profile')
        if Req is None or Prof is None:
            return ok({'items': [], 'online_count': 0})
        reqs = Req.sudo().search([
            ('product_id', '=', product_id),
            ('state', '=', 'completed'),
            ('reviewer_verdict', '!=', False),
        ], order='write_date desc', limit=int(kw.get('limit') or 3))
        items = []
        for r in reqs:
            items.append({
                'id': r.id,
                'reviewer': _reviewer_json(r.reviewer_id),
                'verdict': r.reviewer_verdict,
                'verdict_label': VERDICT_LABEL.get(
                    r.reviewer_verdict, VERDICT_LABEL['neutral']),
                'notes': (r.reviewer_notes or '')[:300],
                'quality': int(r.quality_rating or 0),
                'value': int(r.value_rating or 0),
                'date': r.write_date.strftime('%Y-%m-%d')
                        if r.write_date else '',
            })
        online = Prof.sudo().search_count([
            ('state', '=', 'approved'), ('is_online', '=', True)])
        return ok({'items': items, 'online_count': online})

    @http.route('/api/mobile/v2/reviewers/online', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def reviewers_online(self, **kw):
        Prof = request.env.get('reviewer.profile')
        if Prof is None:
            return ok([])
        revs = Prof.sudo().search([('state', '=', 'approved')],
                                  order='is_online desc, rating desc',
                                  limit=20)
        return ok([_reviewer_json(r) for r in revs])

    @http.route('/api/mobile/v2/reviewers/request', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def reviewer_request(self, **kw):
        p = get_payload()
        partner = current_partner()
        Req = request.env.get('review.request')
        Prof = request.env.get('reviewer.profile')
        if Req is None or Prof is None:
            return fail('UNAVAILABLE', 'Reviewers module not installed', 503)
        try:
            reviewer_id = int(p.get('reviewer_id') or 0)
            product_id = int(p.get('product_id') or 0)
        except Exception:
            return fail('BAD_REQUEST', 'reviewer_id and product_id required')
        rv = Prof.sudo().browse(reviewer_id)
        if not rv.exists() or rv.state != 'approved':
            return fail('NOT_FOUND', 'Reviewer not found', 404)
        session = (p.get('session_type') or 'written').strip()
        if session not in ('written', 'chat', 'photo', 'video'):
            session = 'written'
        req = Req.sudo().create({
            'reviewer_id': rv.id,
            'customer_id': partner.id,
            'product_id': product_id or False,
            'session_type': session,
        })
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': req.id, 'token': req.token, 'state': req.state})
