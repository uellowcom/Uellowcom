import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class LoyaltyController(http.Controller):

    def _get_account(self):
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return None
        partner = request.env.user.partner_id
        return request.env['loyalty.account'].sudo().get_or_create(partner.id)

    # ── Get balance ───────────────────────────────────────────────────────────

    @http.route('/loyalty/balance', type='json', auth='public', methods=['POST'], csrf=False)
    def get_balance(self, **kwargs):
        acc = self._get_account()
        if not acc:
            return {'logged_in': False, 'points': 0}
        return {'logged_in': True, **acc.to_dict()}

    # ── Get transactions ──────────────────────────────────────────────────────

    @http.route('/loyalty/transactions', type='json', auth='user', methods=['POST'], csrf=False)
    def get_transactions(self, **kwargs):
        acc = self._get_account()
        if not acc:
            return {'error': 'Not logged in'}
        limit = int(kwargs.get('limit', 20))
        txns  = acc.transaction_ids[:limit]
        return {
            'account':      acc.to_dict(),
            'transactions': [t.to_dict() for t in txns],
        }

    # ── Redeem points ─────────────────────────────────────────────────────────

    @http.route('/loyalty/redeem', type='json', auth='user', methods=['POST'], csrf=False)
    def redeem_points(self, **kwargs):
        acc    = self._get_account()
        points = int(kwargs.get('points', 0))
        if not acc:
            return {'error': 'Not logged in'}
        if points <= 0:
            return {'error': 'Invalid points amount'}
        if points > acc.points_balance:
            return {'error': f'رصيدك {acc.points_balance} نقطة فقط'}

        order = request.website.sale_get_order()
        if not order:
            return {'error': 'No active cart'}

        kd_value = round(points * 0.001, 3)
        success  = acc.spend_points(
            points,
            f'استبدال {points} نقطة بخصم {kd_value} KD',
            order_id=order.id,
        )

        if success:
            # Apply discount to order (as price reduction)
            try:
                disc_line = order.order_line.filtered(
                    lambda l: l.product_id.name == 'Loyalty Discount'
                )
                if disc_line:
                    disc_line.write({'price_unit': -kd_value})
                else:
                    # Find or create loyalty product
                    loyalty_product = request.env['product.product'].sudo().search(
                        [('name', '=', 'Loyalty Discount')], limit=1
                    )
                    if not loyalty_product:
                        loyalty_product = request.env['product.product'].sudo().create({
                            'name':  'Loyalty Discount',
                            'type':  'service',
                            'sale_ok': True,
                        })
                    order.order_line.sudo().create({
                        'order_id':   order.id,
                        'product_id': loyalty_product.id,
                        'price_unit': -kd_value,
                        'product_uom_qty': 1,
                        'name': f'خصم نقاط الولاء ({points} نقطة)',
                    })
            except Exception as e:
                _logger.warning('Could not apply loyalty discount to cart: %s', e)

            return {
                'success':    True,
                'points_used': points,
                'kd_saved':   kd_value,
                'new_balance': acc.points_balance,
            }
        return {'error': 'فشل الاستبدال'}

    # ── Award points manually ─────────────────────────────────────────────────

    @http.route('/loyalty/award', type='json', auth='public', methods=['POST'], csrf=False)
    def award_points(self, **kwargs):
        """Called internally after events — review written, referral, etc."""
        reason_key = kwargs.get('reason', 'purchase')
        ref        = kwargs.get('ref', '')

        acc = self._get_account()
        if not acc:
            return {'error': 'Not logged in'}

        from odoo.addons.uellow_loyalty.models.loyalty_account import EARN_RATES
        points = EARN_RATES.get(reason_key, 0)

        if points > 0:
            reason_labels = {
                'review':           'كتابة مراجعة منتج',
                'referral':         'دعوة صديق جديد',
                'reviewer_session': 'استخدام الريفيور',
                'birthday':         'عيد ميلاد سعيد! 🎂',
            }
            acc.add_points(points, reason_labels.get(reason_key, reason_key), ref=ref)
            return {'success': True, 'points_awarded': points, 'new_balance': acc.points_balance}

        return {'error': 'Unknown reason'}

    # ── Portal page ───────────────────────────────────────────────────────────

    @http.route('/loyalty', type='http', auth='user', website=True)
    def loyalty_portal(self, **kwargs):
        acc = self._get_account()
        return request.render('uellow_loyalty.loyalty_portal_page', {
            'account': acc,
        })

    # ── Referral System ───────────────────────────────────────────────────────

    @http.route('/loyalty/referral/link', type='json', auth='user', methods=['POST'], csrf=False)
    def get_referral_link(self, **kwargs):
        acc = self._get_account()
        if not acc:
            return {'error': 'Not logged in'}
        partner   = request.env.user.partner_id
        ref_code  = f'REF{partner.id}'
        ref_url   = f'https://uellow.com/shop?ref={ref_code}'
        return {
            'success':   True,
            'ref_code':  ref_code,
            'ref_url':   ref_url,
            'points_reward': 200,
            'message':   'شارك الرابط — تكسب 200 نقطة عند أول شراء للمدعو',
        }

    @http.route('/loyalty/referral/register', type='json', auth='public', methods=['POST'], csrf=False)
    def register_referral(self, **kwargs):
        """Called when new user registers via referral link."""
        ref_code   = kwargs.get('ref_code', '')
        new_partner = kwargs.get('partner_id')
        if not ref_code or not new_partner:
            return {'error': 'Missing params'}
        try:
            referrer_id = int(ref_code.replace('REF', ''))
            referrer    = request.env['res.partner'].sudo().browse(referrer_id)
            if referrer.exists():
                acc = request.env['loyalty.account'].sudo().get_or_create(referrer_id)
                acc.add_points(200, f'دعوة صديق جديد', ref=f'REF-{new_partner}')
                return {'success': True, 'points_awarded': 200}
        except Exception as e:
            return {'error': str(e)}
        return {'error': 'Invalid referral code'}

    # ── Birthday Bonus ────────────────────────────────────────────────────────

    @http.route('/loyalty/birthday/check', type='json', auth='user', methods=['POST'], csrf=False)
    def check_birthday(self, **kwargs):
        """Check and award birthday bonus."""
        acc = self._get_account()
        if not acc:
            return {'error': 'Not logged in'}

        import datetime
        partner = request.env.user.partner_id
        today   = datetime.date.today()

        # Check if partner has birthday set
        if not partner.birthday if hasattr(partner, 'birthday') else True:
            return {'birthday': False}

        try:
            bday = partner.birthday
            if hasattr(bday, 'month'):
                is_birthday = (bday.month == today.month and bday.day == today.day)
            else:
                return {'birthday': False}
        except Exception:
            return {'birthday': False}

        if not is_birthday:
            return {'birthday': False}

        # Check if already given this year
        if acc.birthday_bonus_year == today.year:
            return {'birthday': True, 'already_given': True}

        # Award birthday bonus
        from odoo.addons.uellow_loyalty.models.loyalty_account import EARN_RATES
        points = EARN_RATES.get('birthday', 100)
        acc.add_points(points, 'عيد ميلاد سعيد! 🎂')
        acc.birthday_bonus_year = today.year

        return {
            'birthday':       True,
            'already_given':  False,
            'points_awarded': points,
            'message':        f'عيد ميلاد سعيد! حصلت على {points} نقطة 🎂',
        }

    # ── Review Award ──────────────────────────────────────────────────────────

    @http.route('/loyalty/review/award', type='json', auth='user', methods=['POST'], csrf=False)
    def award_review_points(self, **kwargs):
        """Award points when customer writes a product review."""
        product_id = kwargs.get('product_id')
        acc = self._get_account()
        if not acc:
            return {'error': 'Not logged in'}

        # Check not already awarded for this product
        existing = request.env['loyalty.transaction'].sudo().search([
            ('account_id', '=', acc.id),
            ('reason', 'like', f'مراجعة منتج'),
            ('reference', '=', str(product_id)),
        ], limit=1)

        if existing:
            return {'error': 'Already awarded for this product'}

        from odoo.addons.uellow_loyalty.models.loyalty_account import EARN_RATES
        points = EARN_RATES.get('review', 50)
        acc.add_points(points, 'مراجعة منتج', ref=str(product_id))

        return {
            'success':       True,
            'points_awarded': points,
            'new_balance':   acc.points_balance,
            'message':       f'شكراً على مراجعتك! ربحت {points} نقطة',
        }
