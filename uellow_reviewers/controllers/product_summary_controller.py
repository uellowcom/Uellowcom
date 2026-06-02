# -*- coding: utf-8 -*-
"""
Uellow Reviewers — product_summary_controller.py
Endpoint that powers the in-product-page reviewer card + dialog.
"""

import json
import logging

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class ReviewerProductSummaryController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_reviewers.{key}', default
        )

    def _is_enabled(self):
        return self._get_param('enabled', 'True') in ('True', '1', 'true')

    @http.route('/reviewers/product_summary', type='json', auth='public',
                methods=['POST'], csrf=False)
    def product_summary(self, **kwargs):
        if not self._is_enabled():
            return {'enabled': False}

        product_id = kwargs.get('product_id')
        if not product_id:
            return {'enabled': True, 'error': 'product_id required'}

        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            return {'enabled': True, 'error': 'invalid product_id'}

        product = request.env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return {'enabled': True, 'error': 'product not found'}

        Req = request.env['review.request'].sudo()

        completed = Req.search([
            ('product_id', '=', product_id),
            ('state', '=', 'completed'),
            ('reviewer_verdict', '!=', False),
        ], order='completed_at desc, write_date desc')

        rec_count = len(completed.filtered(lambda r: r.reviewer_verdict == 'recommend'))
        neu_count = len(completed.filtered(lambda r: r.reviewer_verdict == 'neutral'))
        not_count = len(completed.filtered(lambda r: r.reviewer_verdict == 'not_recommend'))
        total_verdicts = rec_count + neu_count + not_count

        recommend_pct = round((rec_count / total_verdicts) * 100) if total_verdicts else 0

        reviewer_ids = completed.mapped('reviewer_id')
        specialists_count = len(reviewer_ids)

        last_opinion = None
        if completed:
            last = completed[0]
            last_opinion = {
                'reviewer_name': last.reviewer_id.display_name or '',
                'reviewer_level': last.reviewer_id.level or 'starter',
                'verdict': last.reviewer_verdict,
                'notes': (last.reviewer_notes or '').strip(),
                'avatar_url': f'/web/image/reviewer.profile/{last.reviewer_id.id}/avatar/64x64'
                              if last.reviewer_id else '',
                'when_ts': last.completed_at.isoformat() if last.completed_at else '',
            }

        online_domain = [('state', '=', 'approved'), ('is_online', '=', True)]
        if product.categ_id:
            online = request.env['reviewer.profile'].sudo().search(
                online_domain + [('specialty_ids', 'in', [product.categ_id.id])],
                limit=8, order='rating desc, review_count desc',
            )
            if len(online) < 8:
                fill = request.env['reviewer.profile'].sudo().search(
                    online_domain + [('id', 'not in', online.ids)],
                    limit=8 - len(online), order='rating desc, review_count desc',
                )
                online = online | fill
        else:
            online = request.env['reviewer.profile'].sudo().search(
                online_domain, limit=8, order='rating desc, review_count desc',
            )

        online_list = [{
            'id': r.id,
            'name': r.display_name or '',
            'level': r.level or 'starter',
            'avatar_url': f'/web/image/reviewer.profile/{r.id}/avatar/64x64',
            'verified': r.verified,
            'allow_written': r.allow_written,
            'allow_chat': r.allow_chat,
        } for r in online]

        featured = online_list[0] if online_list else None

        accepted = Req.search([
            ('product_id', '=', product_id),
            ('accepted_at', '!=', False),
        ], limit=50, order='create_date desc')
        avg_minutes = 0
        if accepted:
            deltas = []
            for r in accepted:
                if r.accepted_at and r.create_date:
                    secs = (r.accepted_at - r.create_date).total_seconds()
                    if 0 <= secs <= 7200:
                        deltas.append(secs)
            if deltas:
                avg_minutes = max(1, round((sum(deltas) / len(deltas)) / 60))

        total_consults = Req.search_count([
            ('product_id', '=', product_id),
            ('state', '=', 'completed'),
        ])

        beena_enabled = request.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'uellow_ai_engine'), ('state', '=', 'installed'),
        ]) > 0

        return {
            'enabled': True,
            'product_id': product_id,
            'stats': {
                'recommend_pct': recommend_pct,
                'recommend': rec_count,
                'neutral': neu_count,
                'not_recommend': not_count,
                'total_verdicts': total_verdicts,
                'specialists_count': specialists_count,
                'total_consults': total_consults,
                'avg_minutes': avg_minutes,
            },
            'online': online_list,
            'online_count': len(online_list),
            'featured': featured,
            'last_opinion': last_opinion,
            'settings': {
                'allow_written': self._get_param('allow_written', 'True') in ('True', '1', 'true'),
                'allow_chat': self._get_param('allow_chat', 'True') in ('True', '1', 'true'),
                'beena_enabled': beena_enabled,
            },
        }
