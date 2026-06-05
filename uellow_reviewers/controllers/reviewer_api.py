# -*- coding: utf-8 -*-
"""
Reviewer mobile API — /api/mobile/v2/reviewer/*  (bearer token auth,
same backend account as the shopping app). Powers the standalone
Uellow Reviewers application.
"""
import json
from datetime import datetime, timedelta

from odoo import http, fields as ofields
from odoo.http import request

from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
    safe_endpoint, ok, fail, get_payload, current_partner, require_auth,
)


def _my_reviewer():
    partner = current_partner()
    if not partner:
        return None
    Prof = request.env['reviewer.profile'].sudo()
    return Prof.search([('partner_id', '=', partner.id)], limit=1) \
        or Prof.search([('partner_id', '=',
                         partner.commercial_partner_id.id)],
                       limit=1) or None


def _icp(key, default):
    return request.env['ir.config_parameter'].sudo().get_param(
        'uellow_reviewers.' + key, default)


class UellowReviewerAPI(http.Controller):

    # ── dashboard ────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/reviewer/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        r = _my_reviewer()
        if not r:
            return ok({'status': 'none'})
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        pts_month = sum(p.points for p in r.point_ids
                        if p.points > 0 and p.create_date
                        and p.create_date >= month_start)
        done_month = len(r.request_ids.filtered(
            lambda q: q.state == 'completed' and q.completed_at
            and q.completed_at >= month_start))
        rate = float(_icp('points_per_kd', '100') or 100)
        return ok({
            'status': r.state,
            'name': r.display_name,
            'bio': r.bio or '',
            'avatar_url': '/web/image/reviewer.profile/%d/avatar/128x128'
                          % r.id,
            'level': r.level,
            'rating': round(r.rating, 1),
            'is_online': r.is_online,
            'verified': r.verified,
            'review_count': r.review_count,
            'purchase_count': r.purchase_count,
            'conversion_rate': r.conversion_rate,
            'points_balance': r.points_balance,
            'points_earned_total': r.points_earned_total,
            'points_month': pts_month,
            'done_month': done_month,
            'wallet_kd': round(r.wallet_balance, 3),
            'total_earned_kd': round(r.total_earned, 3),
            'profit_earned_kd': round(r.profit_earned_total, 3),
            'points_per_kd': rate,
            'min_redeem_points': int(float(_icp('min_redeem_points',
                                               '500') or 500)),
            'min_payout_kd': float(_icp('min_payout', '5') or 5),
            'profit_share_pct': float(_icp('profit_share_pct', '3') or 3),
            'pending_requests': len(r.request_ids.filtered(
                lambda q: q.state == 'pending')),
            'specialties': [c.name for c in r.specialty_ids],
            'specialty_text': r.specialty_text or '',
            'allow': {
                'written': r.allow_written, 'chat': r.allow_chat,
                'photo': r.allow_photo, 'video': r.allow_video,
            },
        })

    @http.route('/api/mobile/v2/reviewer/apply', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def apply(self, **kw):
        partner = current_partner()
        if _my_reviewer():
            return fail('ALREADY', 'You already have a reviewer profile',
                        400)
        p = get_payload()
        prof = request.env['reviewer.profile'].sudo().create({
            'partner_id': partner.id,
            'display_name': (p.get('name') or partner.name or '').strip()
                            or partner.name,
            'bio': (p.get('bio') or '').strip(),
            'specialty_text': (p.get('specialties') or '').strip(),
        })
        return ok({'status': prof.state})

    @http.route('/api/mobile/v2/reviewer/toggle-online', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def toggle_online(self, **kw):
        r = _my_reviewer()
        if not r or r.state != 'approved':
            return fail('NOT_REVIEWER', 'Approved reviewer required', 403)
        r.is_online = not r.is_online
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'is_online': r.is_online})

    # ── requests inbox ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/reviewer/requests', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def requests_list(self, **kw):
        r = _my_reviewer()
        if not r:
            return fail('NOT_REVIEWER', 'Reviewer profile required', 403)
        p = get_payload()
        state = (p.get('state') or '').strip()
        dom = [('reviewer_id', '=', r.id)]
        if state == 'inbox':
            dom.append(('state', 'in', ('pending', 'accepted', 'active')))
        elif state:
            dom.append(('state', '=', state))
        recs = request.env['review.request'].sudo().search(
            dom, order='create_date desc', limit=80)
        return ok({'requests': [q.to_dict() for q in recs]})

    @http.route('/api/mobile/v2/reviewer/requests/<int:rid>/accept',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def request_accept(self, rid, **kw):
        r = _my_reviewer()
        req = request.env['review.request'].sudo().browse(rid)
        if not r or not req.exists() or req.reviewer_id.id != r.id:
            return fail('NOT_FOUND', 'Request not found', 404)
        if req.state != 'pending':
            return fail('BAD_STATE', 'Request is not pending', 400)
        req.action_accept()
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok(req.to_dict())

    @http.route('/api/mobile/v2/reviewer/requests/<int:rid>/complete',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def request_complete(self, rid, **kw):
        r = _my_reviewer()
        req = request.env['review.request'].sudo().browse(rid)
        if not r or not req.exists() or req.reviewer_id.id != r.id:
            return fail('NOT_FOUND', 'Request not found', 404)
        if req.state not in ('pending', 'accepted', 'active'):
            return fail('BAD_STATE', 'Session already closed', 400)
        p = get_payload()
        if req.state == 'pending':
            req.action_accept()
        vals = {}
        for f, key in (('quality_rating', 'quality'),
                       ('value_rating', 'value'),
                       ('comfort_rating', 'comfort')):
            if p.get(key) is not None:
                try:
                    vals[f] = max(0, min(5, int(p[key])))
                except Exception:
                    pass
        if vals:
            req.write(vals)
        req.action_complete(verdict=(p.get('verdict') or '').strip()
                            or None,
                            notes=(p.get('notes') or '').strip() or None)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'state': req.state,
                   'points_awarded': req.points_awarded})

    @http.route('/api/mobile/v2/reviewer/requests/<int:rid>/message',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def request_message(self, rid, **kw):
        r = _my_reviewer()
        req = request.env['review.request'].sudo().browse(rid)
        if not r or not req.exists() or req.reviewer_id.id != r.id:
            return fail('NOT_FOUND', 'Request not found', 404)
        p = get_payload()
        text = (p.get('text') or '').strip()
        if not text:
            return fail('BAD_REQUEST', 'text required')
        req.add_message('reviewer', text)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'messages': req.get_messages()})

    # ── points / wallet ──────────────────────────────────────────────
    @http.route('/api/mobile/v2/reviewer/points', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def points(self, **kw):
        r = _my_reviewer()
        if not r:
            return fail('NOT_REVIEWER', 'Reviewer profile required', 403)
        return ok({'entries': [{
            'id': p.id,
            'date': p.create_date.isoformat() if p.create_date else None,
            'source': p.source,
            'points': p.points,
            'kd_amount': round(p.kd_amount, 3),
            'note': p.note or '',
        } for p in r.point_ids]})

    @http.route('/api/mobile/v2/reviewer/redeem', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def redeem(self, **kw):
        r = _my_reviewer()
        if not r or r.state != 'approved':
            return fail('NOT_REVIEWER', 'Approved reviewer required', 403)
        p = get_payload()
        try:
            kd = r.action_redeem_points(p.get('points'))
            request.env.cr.commit()
        except Exception as e:
            return fail('REDEEM_FAILED', str(e), 400)
        return ok({'kd_credited': kd,
                   'points_balance': r.points_balance,
                   'wallet_kd': round(r.wallet_balance, 3)})

    @http.route('/api/mobile/v2/reviewer/payouts', type='http',
                auth='public', methods=['GET', 'POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def payouts(self, **kw):
        r = _my_reviewer()
        if not r:
            return fail('NOT_REVIEWER', 'Reviewer profile required', 403)
        Pay = request.env['reviewer.commission'].sudo()
        if request.httprequest.method == 'GET':
            recs = Pay.search([('reviewer_id', '=', r.id)],
                              order='create_date desc')
            return ok({'payouts': [{
                'id': x.id,
                'amount': round(x.amount, 3),
                'method': getattr(x, 'method', '') or '',
                'state': x.state,
                'date': x.create_date.isoformat()
                        if x.create_date else None,
            } for x in recs]})
        p = get_payload()
        try:
            amount = float(p.get('amount') or 0)
        except Exception:
            amount = 0
        min_payout = float(_icp('min_payout', '5') or 5)
        if amount < min_payout:
            return fail('TOO_SMALL',
                        'Minimum payout is %.3f KD / الحد الأدنى %.3f'
                        % (min_payout, min_payout), 400)
        if amount > r.wallet_balance + 0.0001:
            return fail('INSUFFICIENT',
                        'Amount exceeds your wallet / المبلغ أكبر من '
                        'رصيدك', 400)
        pay = Pay.create({
            'reviewer_id': r.id,
            'amount': amount,
            'method': (p.get('method') or 'knet').strip(),
            'details': (p.get('details') or '').strip(),
            'period_start': ofields.Date.today(),
            'period_end': ofields.Date.today(),
        })
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': pay.id, 'state': pay.state})

    # ── leaderboard ──────────────────────────────────────────────────
    @http.route('/api/mobile/v2/reviewer/leaderboard', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def leaderboard(self, **kw):
        me = _my_reviewer()
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        rows = request.env['reviewer.point'].sudo().search([
            ('create_date', '>=', month_start),
            ('points', '>', 0),
        ])
        totals = {}
        for p in rows:
            totals[p.reviewer_id.id] = \
                totals.get(p.reviewer_id.id, 0) + p.points
        ranked = sorted(totals.items(), key=lambda kv: -kv[1])
        Prof = request.env['reviewer.profile'].sudo()
        out, my_rank = [], None
        for i, (pid, pts) in enumerate(ranked):
            prof = Prof.browse(pid)
            masked = (prof.display_name or '?')
            if len(masked) > 3:
                masked = masked[:3] + '***'
            if me and pid == me.id:
                my_rank = i + 1
                masked = prof.display_name
            if i < 10:
                out.append({'rank': i + 1, 'name': masked,
                            'level': prof.level, 'points': pts,
                            'me': bool(me and pid == me.id)})
        return ok({'top': out, 'my_rank': my_rank})
