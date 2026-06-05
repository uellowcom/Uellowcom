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
                      current_partner, require_auth, bilingual)

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

    @http.route('/api/mobile/v2/reviewers/my-requests', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def my_requests(self, **kw):
        """v2.1.54 — the customer's specialist requests with replies,
        verdicts and group-vote tallies (My Sizes screen)."""
        partner = current_partner()
        Req = request.env.get('review.request')
        if Req is None:
            return ok({'items': []})
        reqs = Req.sudo().search([('customer_id', '=', partner.id)],
                                 order='create_date desc', limit=30)
        STATE_LBL = {
            'pending':   {'en': 'Waiting for reviewer', 'ar': 'بانتظار المراجع'},
            'accepted':  {'en': 'Accepted',  'ar': 'قَبِل الطلب'},
            'active':    {'en': 'In session', 'ar': 'جلسة نشطة'},
            'completed': {'en': 'Replied',   'ar': 'تم الرد'},
            'expired':   {'en': 'Expired',   'ar': 'منتهي'},
            'cancelled': {'en': 'Cancelled', 'ar': 'ملغي'},
        }
        items = []
        seen_batches = set()
        for r in reqs:
            # group-vote pools render once with the tally
            votes = None
            if r.batch_token:
                if r.batch_token in seen_batches:
                    continue
                seen_batches.add(r.batch_token)
                pool = reqs.filtered(
                    lambda x: x.batch_token == r.batch_token)
                done = pool.filtered(lambda x: x.reviewer_verdict)
                votes = {
                    'total': len(pool),
                    'voted': len(done),
                    'recommend': len(done.filtered(
                        lambda x: x.reviewer_verdict == 'recommend')),
                    'not_recommend': len(done.filtered(
                        lambda x: x.reviewer_verdict == 'not_recommend')),
                    'neutral': len(done.filtered(
                        lambda x: x.reviewer_verdict == 'neutral')),
                }
            replies = []
            try:
                for m in r.get_messages():
                    if m.get('sender') == 'reviewer' and m.get('text'):
                        replies.append({
                            'text': str(m.get('text'))[:400],
                            'at': str(m.get('timestamp') or '')[:16],
                        })
            except Exception:
                pass
            tmpl = r.product_id
            items.append({
                'id': r.id,
                'state': r.state,
                'state_label': STATE_LBL.get(r.state, STATE_LBL['pending']),
                'session_type': r.session_type,
                'date': r.create_date.strftime('%Y-%m-%d %H:%M')
                        if r.create_date else '',
                'product': {
                    'id': tmpl.id if tmpl else 0,
                    'name': bilingual(tmpl, 'name') if tmpl else
                            {'en': '', 'ar': ''},
                    'image': img_url('product.template', tmpl.id,
                                     'image_128', unique=tmpl.write_date)
                             if tmpl else None,
                },
                'reviewer': _reviewer_json(r.reviewer_id)
                            if r.reviewer_id else None,
                'verdict': r.reviewer_verdict or '',
                'verdict_label': VERDICT_LABEL.get(
                    r.reviewer_verdict, None) if r.reviewer_verdict else None,
                'notes': (r.reviewer_notes or '')[:400],
                'quality': int(r.quality_rating or 0),
                'value': int(r.value_rating or 0),
                'replies': replies[-3:],
                'votes': votes,
            })
        return ok({'items': items})

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
        vals = {
            'reviewer_id': rv.id,
            'customer_id': partner.id,
            'product_id': product_id or False,
            'session_type': session,
        }
        # v2.1.35 — optional customer question, seeded as the first chat
        # message so the specialist sees it immediately.
        note = (p.get('note') or '').strip()[:500]
        if note and 'messages_json' in Req._fields:
            import json as _json
            from datetime import datetime as _dt
            vals['messages_json'] = _json.dumps([{
                'from': 'customer',
                'text': note,
                'at': _dt.now().isoformat(timespec='seconds'),
            }])
        req = Req.sudo().create(vals)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': req.id, 'token': req.token, 'state': req.state})
