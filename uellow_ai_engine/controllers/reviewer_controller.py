import json
import logging
import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ReviewerController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_reviewers.{key}', default
        )

    def _is_enabled(self):
        return self._get_param('enabled', 'True') in ('True', '1', 'true')

    # ── Get online reviewers ──────────────────────────────────────────────────

    @http.route('/reviewers/online', type='json', auth='public', methods=['POST'], csrf=False)
    def get_online_reviewers(self, **kwargs):
        if not self._is_enabled():
            return {'reviewers': [], 'enabled': False}

        product_id = kwargs.get('product_id')
        limit      = int(kwargs.get('limit', 10))

        domain = [
            ('state', '=', 'approved'),
            ('is_online', '=', True),
        ]

        # Filter by product category if provided
        if product_id:
            product = request.env['product.template'].sudo().browse(int(product_id))
            if product.exists() and product.categ_id:
                # Prefer reviewers who specialize in this category
                specialized = request.env['reviewer.profile'].sudo().search(
                    domain + [('specialty_ids', 'in', [product.categ_id.id])],
                    limit=limit,
                )
                general = request.env['reviewer.profile'].sudo().search(
                    domain + [('id', 'not in', specialized.ids)],
                    limit=max(0, limit - len(specialized)),
                )
                reviewers = specialized | general
            else:
                reviewers = request.env['reviewer.profile'].sudo().search(domain, limit=limit)
        else:
            reviewers = request.env['reviewer.profile'].sudo().search(domain, limit=limit)

        # Also get offline reviewers to fill up to limit
        offline_domain = [('state', '=', 'approved'), ('is_online', '=', False)]
        offline = request.env['reviewer.profile'].sudo().search(
            offline_domain, limit=max(0, limit - len(reviewers)),
            order='rating desc, review_count desc',
        )

        all_reviewers = list(reviewers) + list(offline)

        return {
            'enabled':   True,
            'reviewers': [r.to_dict() for r in all_reviewers],
            'total_online': len(reviewers),
            'settings': {
                'allow_written': self._get_param('allow_written', 'True') in ('True','1','true'),
                'allow_chat':    self._get_param('allow_chat',    'True') in ('True','1','true'),
                'allow_photo':   self._get_param('allow_photo',   'True') in ('True','1','true'),
                'allow_video':   self._get_param('allow_video',   'False') in ('True','1','true'),
                'max_count':     int(self._get_param('max_reviewers', '5')),
            },
        }

    # ── Create review request ─────────────────────────────────────────────────

    @http.route('/reviewers/request', type='json', auth='public', methods=['POST'], csrf=False)
    def create_request(self, **kwargs):
        if not self._is_enabled():
            return {'error': 'Reviewer system disabled'}

        reviewer_id  = kwargs.get('reviewer_id')
        product_id   = kwargs.get('product_id')
        session_type = kwargs.get('session_type', 'written')

        if not reviewer_id:
            return {'error': 'reviewer_id required'}

        reviewer = request.env['reviewer.profile'].sudo().browse(int(reviewer_id))
        if not reviewer.exists() or reviewer.state != 'approved':
            return {'error': 'Reviewer not available'}

        if not reviewer.is_online:
            return {'error': 'Reviewer is offline'}

        # Validate session type is allowed
        type_map = {
            'written': reviewer.allow_written,
            'chat':    reviewer.allow_chat,
            'photo':   reviewer.allow_photo,
            'video':   reviewer.allow_video,
        }
        if not type_map.get(session_type, False):
            return {'error': f'Session type {session_type} not available for this reviewer'}

        # Get customer
        public_user = request.env.ref('base.public_user')
        customer_id = None
        if request.env.user.id != public_user.id:
            customer_id = request.env.user.partner_id.id

        # Fee based on type
        fee_map = {'written': reviewer.price_written, 'chat': reviewer.price_chat}
        fee = fee_map.get(session_type, reviewer.price_written)

        # Expiry
        expiry_minutes = int(self._get_param('request_expiry', '10'))

        review_req = request.env['review.request'].sudo().create({
            'reviewer_id':  reviewer.id,
            'customer_id':  customer_id,
            'product_id':   int(product_id) if product_id else False,
            'session_type': session_type,
            'fee':          fee,
            'expires_at':   datetime.datetime.now() + datetime.timedelta(minutes=expiry_minutes),
        })

        return {
            'success':    True,
            'request_id': review_req.id,
            'token':      review_req.token,
            'fee':        fee,
            'expires_in': expiry_minutes * 60,  # seconds
        }

    # ── Get request status ────────────────────────────────────────────────────

    @http.route('/reviewers/request/<string:token>', type='json', auth='public', methods=['POST'], csrf=False)
    def get_request(self, token, **kwargs):
        req = request.env['review.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not req:
            return {'error': 'Request not found'}
        return {'request': req.to_dict()}

    # ── Send message in session ───────────────────────────────────────────────

    @http.route('/reviewers/message', type='json', auth='public', methods=['POST'], csrf=False)
    def send_message(self, **kwargs):
        token   = kwargs.get('token')
        text    = (kwargs.get('text') or '').strip()
        sender  = kwargs.get('sender', 'customer')  # 'customer' or 'reviewer'

        if not token or not text:
            return {'error': 'token and text required'}

        req = request.env['review.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not req:
            return {'error': 'Request not found'}

        if req.state not in ('accepted', 'active'):
            return {'error': 'Session not active'}

        # Activate if first message
        if req.state == 'accepted':
            req.state = 'active'

        req.add_message(sender, text)

        return {
            'success':  True,
            'messages': req.get_messages(),
        }

    # ── Submit verdict (reviewer) ─────────────────────────────────────────────

    @http.route('/reviewers/verdict', type='json', auth='public', methods=['POST'], csrf=False)
    def submit_verdict(self, **kwargs):
        token   = kwargs.get('token')
        verdict = kwargs.get('verdict')  # recommend / not_recommend / neutral
        notes   = kwargs.get('notes', '')
        quality = int(kwargs.get('quality_rating', 0))
        value   = int(kwargs.get('value_rating', 0))
        comfort = int(kwargs.get('comfort_rating', 0))

        req = request.env['review.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not req:
            return {'error': 'Request not found'}

        req.write({
            'reviewer_verdict': verdict,
            'reviewer_notes':   notes,
            'quality_rating':   quality,
            'value_rating':     value,
            'comfort_rating':   comfort,
        })
        req.action_complete(verdict=verdict, notes=notes)

        return {'success': True, 'request': req.to_dict()}

    # ── Reviewer: accept/decline request ─────────────────────────────────────

    @http.route('/reviewers/accept', type='json', auth='user', methods=['POST'], csrf=False)
    def accept_request(self, **kwargs):
        request_id = kwargs.get('request_id')
        action     = kwargs.get('action', 'accept')  # accept or decline

        req = request.env['review.request'].sudo().browse(int(request_id))
        if not req.exists():
            return {'error': 'Request not found'}

        if action == 'accept':
            req.action_accept()
            return {'success': True, 'token': req.token, 'state': 'accepted'}
        else:
            req.action_expire()
            return {'success': True, 'state': 'expired'}

    # ── Reviewer: toggle online status ────────────────────────────────────────

    @http.route('/reviewers/toggle_online', type='json', auth='user', methods=['POST'], csrf=False)
    def toggle_online(self, **kwargs):
        reviewer = request.env['reviewer.profile'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)], limit=1
        )
        if not reviewer:
            return {'error': 'Not a reviewer'}

        reviewer.toggle_online()
        return {'is_online': reviewer.is_online}

    # ── Reviewer: get my dashboard ────────────────────────────────────────────

    @http.route('/reviewers/dashboard', type='json', auth='user', methods=['POST'], csrf=False)
    def get_dashboard(self, **kwargs):
        reviewer = request.env['reviewer.profile'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id)], limit=1
        )
        if not reviewer:
            return {'error': 'Not a reviewer', 'is_reviewer': False}

        # Pending requests
        pending = request.env['review.request'].sudo().search([
            ('reviewer_id', '=', reviewer.id),
            ('state', '=', 'pending'),
        ], limit=10)

        # Active session
        active = request.env['review.request'].sudo().search([
            ('reviewer_id', '=', reviewer.id),
            ('state', 'in', ('accepted', 'active')),
        ], limit=1)

        return {
            'is_reviewer':    True,
            'reviewer':       reviewer.to_dict(),
            'pending_requests': [r.to_dict() for r in pending],
            'active_session': active.to_dict() if active else None,
            'wallet':         reviewer.wallet_balance,
            'total_earned':   reviewer.total_earned,
        }

    # ── Customer: rate reviewer ───────────────────────────────────────────────

    @http.route('/reviewers/rate', type='json', auth='public', methods=['POST'], csrf=False)
    def rate_reviewer(self, **kwargs):
        token  = kwargs.get('token')
        rating = int(kwargs.get('rating', 5))
        review = kwargs.get('review', '')

        req = request.env['review.request'].sudo().search(
            [('token', '=', token)], limit=1
        )
        if not req or req.state != 'completed':
            return {'error': 'Request not found or not completed'}

        req.write({'customer_rating': rating, 'customer_review': review})

        # Update reviewer average rating
        reviewer    = req.reviewer_id
        all_ratings = request.env['review.request'].sudo().search([
            ('reviewer_id', '=', reviewer.id),
            ('customer_rating', '>', 0),
        ])
        if all_ratings:
            avg = sum(r.customer_rating for r in all_ratings) / len(all_ratings)
            reviewer.rating = round(avg, 2)

        return {'success': True}

    # ── Register as reviewer ──────────────────────────────────────────────────

    @http.route('/reviewers/register', type='json', auth='user', methods=['POST'], csrf=False)
    def register_reviewer(self, **kwargs):
        partner = request.env.user.partner_id
        existing = request.env['reviewer.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1
        )
        if existing:
            return {'error': 'Already registered', 'reviewer_id': existing.id}

        display_name  = kwargs.get('display_name', partner.name)
        bio           = kwargs.get('bio', '')
        specialty_ids = kwargs.get('specialty_ids', [])

        require_approval = self._get_param('require_approval', 'True') in ('True','1','true')

        reviewer = request.env['reviewer.profile'].sudo().create({
            'partner_id':   partner.id,
            'display_name': display_name,
            'bio':          bio,
            'specialty_ids': [(6, 0, specialty_ids)],
            'state':        'pending' if require_approval else 'approved',
        })

        return {
            'success':     True,
            'reviewer_id': reviewer.id,
            'state':       reviewer.state,
            'message':     'تم التسجيل — بانتظار الموافقة' if require_approval else 'تم التسجيل بنجاح',
        }

    # ── Portal Pages ──────────────────────────────────────────────────────────

    @http.route('/reviewer/dashboard', type='http', auth='user', website=True)
    def reviewer_portal(self, **kwargs):
        """Main reviewer portal page."""
        return request.render('uellow_reviewers.reviewer_dashboard_page', {})

    @http.route('/reviewer/register', type='http', auth='user', website=True)
    def reviewer_register_page(self, **kwargs):
        """Reviewer registration page."""
        return request.render('uellow_reviewers.reviewer_register_page', {})
