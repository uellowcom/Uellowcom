"""Loyalty + Wallet — /api/mobile/v2/loyalty/* and /wallet/*

Loyalty is sourced from Odoo's LIVE loyalty.card (per CLAUDE.md the only
source with real customer data — 3911 customers). Tier thresholds, earn
rules and perks are read from uellow.loyalty.program / .tier.rule.
Redemption issues a fresh loyalty.card with a code the customer can
type at checkout (works with the existing cart/apply-coupon flow).
"""
from datetime import date, datetime, timedelta
from secrets import choice
from string import ascii_uppercase, digits

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    fmt_price, bilingual,
)


# ─── Helpers ─────────────────────────────────────────────────────────

def _tier_thresholds_and_rate():
    """Read tier thresholds + redeem rate from uellow.loyalty.program."""
    Prog = request.env.get('uellow.loyalty.program')
    thresholds = {'silver': 1000, 'gold': 5000, 'platinum': 15000}
    redeem_rate = 100
    min_redeem = 100
    multipliers = {'silver': 1.5, 'gold': 2.0, 'platinum': 3.0}
    earn = {
        'per_kd':         10,
        'review_text':    5,
        'review_photo':   15,
        'review_video':   30,
        'referral':       50,
        'first_purchase': 100,
        'birthday':       200,
    }
    if Prog is not None:
        prog = Prog.sudo().search([], limit=1)
        if prog:
            thresholds = {
                'silver':   int(getattr(prog, 'tier_silver_min', 1000)),
                'gold':     int(getattr(prog, 'tier_gold_min', 5000)),
                'platinum': int(getattr(prog, 'tier_platinum_min', 15000)),
            }
            redeem_rate = int(getattr(prog, 'points_per_kd_redeem', 100))
            min_redeem  = int(getattr(prog, 'min_points_redeem', 100))
            multipliers = {
                'silver':   float(getattr(prog, 'silver_multiplier', 1.5)),
                'gold':     float(getattr(prog, 'gold_multiplier',   2.0)),
                'platinum': float(getattr(prog, 'platinum_multiplier', 3.0)),
            }
            earn = {
                'per_kd':         float(getattr(prog, 'points_per_kd', 10)),
                'review_text':    int(getattr(prog, 'points_review_text', 5)),
                'review_photo':   int(getattr(prog, 'points_review_photo', 15)),
                'review_video':   int(getattr(prog, 'points_review_video', 30)),
                'referral':       int(getattr(prog, 'points_referral', 50)),
                'first_purchase': int(getattr(prog, 'points_first_purchase', 100)),
                'birthday':       int(getattr(prog, 'points_birthday', 200)),
            }
    return thresholds, redeem_rate, min_redeem, multipliers, earn


def _tier_for(points, thresholds):
    if points >= thresholds['platinum']: return 'platinum'
    if points >= thresholds['gold']:     return 'gold'
    if points >= thresholds['silver']:   return 'silver'
    return 'bronze'


def _next_tier(current, thresholds):
    order = ['bronze', 'silver', 'gold', 'platinum']
    idx = order.index(current)
    if idx + 1 >= len(order):
        return None, None
    nxt = order[idx + 1]
    return nxt, thresholds.get(nxt)


def _progress_pct(points, tier, thresholds):
    if tier == 'platinum':
        return 100
    target_key = {'bronze':'silver','silver':'gold','gold':'platinum'}[tier]
    target = thresholds.get(target_key, 1)
    return min(100, int(round(points * 100 / target))) if target else 0


def _perks_for(tier):
    """Read uellow.loyalty.tier.rule rows; fall back to baked-in defaults."""
    Rule = request.env.get('uellow.loyalty.tier.rule')
    out = []
    if Rule is not None:
        order = ['bronze', 'silver', 'gold', 'platinum']
        max_idx = order.index(tier)
        for r in Rule.sudo().search([]):
            if order.index(r.tier) <= max_idx:
                out.append({
                    'key':   r.benefit,
                    'value': float(r.value or 0),
                    'label': {
                        'en': r.description or _benefit_label_en(r.benefit, r.value),
                        'ar': _benefit_label_ar(r.benefit, r.value),
                    },
                    'tier':  r.tier,
                })
    if out:
        return out
    # Default perks per tier
    defaults = {
        'bronze':   [('birthday_gift', 0)],
        'silver':   [('free_shipping', 0), ('birthday_gift', 0)],
        'gold':     [('free_shipping', 0), ('early_access', 0),
                     ('birthday_gift', 0), ('discount_voucher', 5)],
        'platinum': [('free_shipping', 0), ('early_access', 0),
                     ('priority_support', 0), ('birthday_gift', 0),
                     ('discount_voucher', 10)],
    }
    return [{
        'key': k,
        'value': v,
        'label': {'en': _benefit_label_en(k, v), 'ar': _benefit_label_ar(k, v)},
        'tier': tier,
    } for k, v in defaults.get(tier, [])]


def _benefit_label_en(key, value):
    return {
        'free_shipping':    'Free shipping on every order',
        'discount_voucher': f'{int(value or 0)} KD welcome voucher',
        'early_access':     'Early access to flash sales',
        'priority_support': 'Priority customer support',
        'birthday_gift':    'Birthday gift each year',
    }.get(key, key)


def _benefit_label_ar(key, value):
    return {
        'free_shipping':    'شحن مجاني لكل طلب',
        'discount_voucher': f'قسيمة ترحيبية بقيمة {int(value or 0)} د.ك',
        'early_access':     'وصول مبكر للعروض الخاطفة',
        'priority_support': 'دعم عملاء بأولوية',
        'birthday_gift':    'هدية عيد ميلاد سنوياً',
    }.get(key, key)


def _earn_ways(earn, redeem_rate):
    """Bilingual earn-ways list, rendered straight from program rules."""
    return [
        {
            'key':    'order',
            'icon':   'cart',
            'title':  {'en': 'Place an order',
                       'ar': 'اطلب أي منتج'},
            'detail': {'en': f"1 KD spent = {int(earn['per_kd'])} points",
                       'ar': f"كل 1 د.ك = {int(earn['per_kd'])} نقطة"},
            'badge':  f"+{int(earn['per_kd'])}/KD",
        },
        {
            'key':    'review',
            'icon':   'star',
            'title':  {'en': 'Write a product review',
                       'ar': 'اكتب تقييم لمنتج'},
            'detail': {'en': f"Text +{earn['review_text']} · Photo +{earn['review_photo']} · Video +{earn['review_video']}",
                       'ar': f"نص +{earn['review_text']} · صورة +{earn['review_photo']} · فيديو +{earn['review_video']}"},
            'badge':  f"+{earn['review_photo']}",
        },
        {
            'key':    'referral',
            'icon':   'person',
            'title':  {'en': 'Refer a friend',
                       'ar': 'ادعُ صديقاً'},
            'detail': {'en': f"You both get +{earn['referral']} points",
                       'ar': f"كلاكما يحصل على +{earn['referral']} نقطة"},
            'badge':  f"+{earn['referral']}",
        },
        {
            'key':    'birthday',
            'icon':   'cake',
            'title':  {'en': 'Birthday bonus',
                       'ar': 'هدية عيد الميلاد'},
            'detail': {'en': f"+{earn['birthday']} points on your birthday",
                       'ar': f"+{earn['birthday']} نقطة في يوم ميلادك"},
            'badge':  f"+{earn['birthday']}",
        },
    ]


def _redeem_options(points, redeem_rate, min_redeem):
    """A handful of preset redemption tiers."""
    KD = lambda p: round(p / redeem_rate, 3) if redeem_rate else 0
    raw = [
        ('5_off',   {'en': '5 KD off any order',
                     'ar': 'خصم 5 د.ك على أي طلب'},
                    int(5 * redeem_rate), '💵'),
        ('10_off',  {'en': '10 KD off any order',
                     'ar': 'خصم 10 د.ك على أي طلب'},
                    int(10 * redeem_rate), '🎁'),
        ('25_off',  {'en': '25 KD off premium orders',
                     'ar': 'خصم 25 د.ك على الطلبات المميزة'},
                    int(25 * redeem_rate), '💎'),
        ('free_ship', {'en': 'Free express shipping',
                       'ar': 'شحن سريع مجاني'},
                    max(min_redeem, int(2 * redeem_rate)), '🚚'),
    ]
    return [{
        'key':    k,
        'label':  l,
        'points': p,
        'kd':     KD(p),
        'icon':   ic,
        'affordable': points >= p,
    } for (k, l, p, ic) in raw]


def _history_for(partner, limit=20):
    """History merges:
       - loyalty.history rows (Odoo native earn/redeem ledger if present)
       - any uellow.loyalty.transaction rows (the in-house ledger)
    Falls back gracefully if neither exists.
    """
    out = []
    # Odoo's loyalty.history exists in 18+ for tracking
    His = request.env.get('loyalty.history')
    if His is not None:
        rows = His.sudo().search([('card_id.partner_id', '=', partner.id)],
                                 order='create_date desc', limit=limit)
        for h in rows:
            pts = float(getattr(h, 'used', 0) or getattr(h, 'issued', 0) or 0)
            is_earn = float(getattr(h, 'issued', 0) or 0) > 0
            # `order_id` is a Many2one — attribute access returns the
            # recordset (or empty), not an int. Guard for both shapes.
            order_field = h.order_id if 'order_id' in h._fields else None
            order_name = ''
            if order_field:
                if hasattr(order_field, 'name'):
                    order_name = order_field.name or ''
                else:
                    try:
                        order_name = request.env['sale.order'].sudo()\
                            .browse(int(order_field)).name or ''
                    except Exception:
                        order_name = ''
            label_en = (f"Order {order_name}" if order_name
                        else (getattr(h, 'description', '') or 'Adjustment'))
            out.append({
                'id':    h.id,
                'when':  (h.create_date or datetime.now()).isoformat(),
                'pts':   int(pts if is_earn else -abs(pts)),
                'is_earn': is_earn,
                'label': {'en': label_en, 'ar': label_en},
            })
    # Also pull from our own ledger if module is loaded
    Tx = request.env.get('uellow.loyalty.transaction')
    if Tx is not None and not out:
        rows = Tx.sudo().search([('partner_id', '=', partner.id)],
                                order='create_date desc', limit=limit)
        for t in rows:
            is_earn = t.tx_type in ('earn', 'adjust') and t.points > 0
            out.append({
                'id':    t.id,
                'when':  (t.date or t.create_date or datetime.now()).isoformat(),
                'pts':   int(t.points if is_earn else -abs(t.points)),
                'is_earn': is_earn,
                'label': {'en': t.reason or t.tx_type.capitalize(),
                          'ar': t.reason or t.tx_type.capitalize()},
            })
    return out[:limit]


def _gen_code(prefix='UEL', length=8):
    chars = ascii_uppercase + digits
    return prefix + '-' + ''.join(choice(chars) for _ in range(length))


# ─── Loyalty endpoints ───────────────────────────────────────────────

class MobileLoyaltyAPI(http.Controller):

    @http.route('/api/mobile/v2/loyalty', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def loyalty_overview(self, **kw):
        partner = current_partner()
        cards = request.env['loyalty.card'].sudo().search([
            ('partner_id', '=', partner.id),
        ])
        total_points = int(sum(cards.mapped('points')))
        thresholds, rate, min_redeem, mult, earn = _tier_thresholds_and_rate()
        tier = _tier_for(total_points, thresholds)
        nxt, nxt_thr = _next_tier(tier, thresholds)
        kd_value = round(total_points / rate, 3) if rate else 0
        return ok({
            'points':         total_points,
            'tier':           tier,
            'tier_label': {
                'en': tier.capitalize(),
                'ar': {'bronze': 'برونزي', 'silver': 'فضي',
                       'gold': 'ذهبي', 'platinum': 'بلاتيني'}[tier],
            },
            'tier_multiplier': mult.get(tier, 1.0),
            'next_tier':      nxt,
            'next_threshold': nxt_thr,
            'points_to_next': max(0, (nxt_thr or total_points) - total_points),
            'progress_pct':   _progress_pct(total_points, tier, thresholds),
            'redeem_rate':    rate,
            'min_redeem':     min_redeem,
            'kd_value':       fmt_price(kd_value),
            'perks':          _perks_for(tier),
            'earn_ways':      _earn_ways(earn, rate),
            'redeem_options': _redeem_options(total_points, rate, min_redeem),
            'history':        _history_for(partner, limit=20),
            'cards': [{
                'id': c.id, 'program': c.program_id.name,
                'points': int(c.points),
                'code': c.code or '',
                'expires': c.expiration_date.isoformat() if c.expiration_date else None,
            } for c in cards],
        })

    @http.route('/api/mobile/v2/loyalty/redeem', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def loyalty_redeem(self, **kw):
        """Redeem points → issue a coupon card the customer can use at
        checkout.  Burns the points off their existing loyalty.card
        balance, then creates a fresh loyalty.card with a usable code.
        Body: { option_key, points }  — points is what they're spending.
        """
        p = get_payload()
        opt_key = (p.get('option_key') or '').strip()
        try:
            spend = int(p.get('points') or 0)
        except (TypeError, ValueError):
            return fail('BAD_INPUT', 'points must be integer')
        partner = current_partner()
        thresholds, rate, min_redeem, *_ = _tier_thresholds_and_rate()
        if spend < min_redeem:
            return fail('TOO_SMALL', f'Minimum redemption is {min_redeem} points')
        # Sum the customer's earning cards (positive points only)
        Card = request.env['loyalty.card'].sudo()
        cards = Card.search([('partner_id', '=', partner.id),
                             ('program_id.program_type', '=', 'loyalty')])
        total = int(sum(cards.mapped('points')))
        if total < spend:
            return fail('NOT_ENOUGH', f'You need {spend} pts but only have {total}')

        # Burn the points pro-rata on those cards
        remaining = spend
        for c in cards:
            if remaining <= 0:
                break
            take = min(int(c.points), remaining)
            if take > 0:
                c.write({'points': c.points - take})
                remaining -= take

        # Build / select a target promotional program for the redeemed
        # discount.  We re-use a single hidden program named
        # 'Uellow Redeemed Points' so the discount code works in cart.
        Program = request.env['loyalty.program'].sudo()
        prog = Program.search([('name', '=', 'Uellow Redeemed Points'),
                               ('program_type', '=', 'promo_code')], limit=1)
        if not prog:
            company = request.env.company
            currency = company.currency_id
            prog = Program.create({
                'name': 'Uellow Redeemed Points',
                'program_type': 'promo_code',
                'applies_on': 'current',
                'active': True,
                'company_id': company.id,
                'currency_id': currency.id,
            })
            # One discount reward
            request.env['loyalty.reward'].sudo().create({
                'program_id': prog.id,
                'reward_type': 'discount',
                'discount_mode': 'per_order',
                'discount': 1,         # placeholder — overridden per card
                'required_points': 1,
            })

        # Compute redemption value
        kd_value = round(spend / rate, 3) if rate else 0
        code = _gen_code('UEL', 8)

        # Create the issued card (this is what the customer will type at
        # checkout). loyalty.card "points" represents the usable balance
        # — for promo_code programs Odoo allows arbitrary point values
        # to express the discount.
        new_card = Card.create({
            'program_id': prog.id,
            'partner_id': partner.id,
            'code':       code,
            'points':     kd_value,
            'expiration_date': date.today() + timedelta(days=90),
        })
        return ok({
            'code':       code,
            'kd_value':   fmt_price(kd_value),
            'card_id':    new_card.id,
            'expires':    new_card.expiration_date.isoformat() if new_card.expiration_date else None,
            'remaining_points': total - spend,
            'option_key': opt_key,
        })


# ─── Wallet endpoints ────────────────────────────────────────────────

class MobileWalletAPI(http.Controller):

    @http.route('/api/mobile/v2/wallet', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def overview(self, **kw):
        """Single round-trip: balance + last 50 transactions + features."""
        partner = current_partner()
        balance = float(getattr(partner, 'wallet_balance', 0) or 0)
        Tx = request.env.get('uellow.customer.wallet.tx')
        txs = []
        if Tx is not None:
            for t in Tx.sudo().search([('partner_id', '=', partner.id)],
                                      order='create_date desc', limit=50):
                txs.append({
                    'id':      t.id,
                    'amount':  fmt_price(t.amount),
                    'type':    t.transaction_type,
                    'state':   t.state,
                    'description': t.description or '',
                    'reference':  t.reference or '',
                    'when':    (t.create_date or datetime.now()).isoformat(),
                    'counter_name': (t.counter_partner_id.name
                                      if t.counter_partner_id else ''),
                    'order_name':   t.order_id.name if t.order_id else '',
                })
        return ok({
            'balance':      fmt_price(balance),
            'transactions': txs,
            'can_send':     True,
            'can_topup':    True,
            'can_giftcard': True,
        })

    @http.route('/api/mobile/v2/wallet/balance', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def balance(self, **kw):
        partner = current_partner()
        bal = float(getattr(partner, 'wallet_balance', 0) or 0)
        return ok({'balance': fmt_price(bal)})

    @http.route('/api/mobile/v2/wallet/transactions', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def transactions(self, **kw):
        partner = current_partner()
        Tx = request.env.get('uellow.customer.wallet.tx')
        if Tx is None:
            return ok([])
        out = []
        for t in Tx.sudo().search([('partner_id', '=', partner.id)],
                                  order='create_date desc', limit=100):
            out.append({
                'id':      t.id,
                'amount':  fmt_price(t.amount),
                'type':    t.transaction_type,
                'state':   t.state,
                'description': t.description or '',
                'reference':  t.reference or '',
                'date':    (t.create_date or datetime.now()).isoformat(),
                'counter_name': (t.counter_partner_id.name
                                  if t.counter_partner_id else ''),
            })
        return ok(out)

    @http.route('/api/mobile/v2/wallet/redeem-gift', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def redeem_gift(self, **kw):
        """Top up the wallet by redeeming a gift-card / promo loyalty.card
        code.  The card's points are interpreted as a currency amount
        (Odoo convention for gift cards)."""
        p = get_payload()
        code = (p.get('code') or '').strip().upper()
        if not code:
            return fail('NO_CODE', 'Gift card code is required')
        partner = current_partner()
        Card = request.env['loyalty.card'].sudo()
        card = Card.search([('code', '=', code)], limit=1)
        if not card:
            return fail('INVALID_CODE', 'Invalid or expired code', 404)
        if card.expiration_date and card.expiration_date < date.today():
            return fail('EXPIRED', 'This code has expired', 410)
        if card.partner_id and card.partner_id != partner:
            return fail('NOT_YOURS', 'This code is for another customer', 403)
        amount = float(card.points or 0)
        if amount <= 0:
            return fail('ZERO', 'This code has no remaining balance', 400)
        # Credit wallet, mark card spent
        Tx = request.env['uellow.customer.wallet.tx'].sudo()
        Tx.credit(partner, amount,
                  tx_type='gift_card',
                  description=f'Gift card {code}',
                  reference=code)
        card.write({'points': 0})
        bal = float(getattr(partner, 'wallet_balance', 0) or 0)
        return ok({
            'credited': fmt_price(amount),
            'balance':  fmt_price(bal),
            'reference': code,
        })

    @http.route('/api/mobile/v2/wallet/send', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def send(self, **kw):
        """Send funds to another customer by phone or email."""
        p = get_payload()
        recipient_q = (p.get('recipient') or '').strip()
        try:
            amount = float(p.get('amount') or 0)
        except (TypeError, ValueError):
            return fail('BAD_AMOUNT', 'amount must be a number')
        note = (p.get('note') or '').strip()
        if amount <= 0:
            return fail('BAD_AMOUNT', 'amount must be positive')
        if not recipient_q:
            return fail('NO_RECIPIENT', 'recipient phone or email required')
        partner = current_partner()
        if float(getattr(partner, 'wallet_balance', 0) or 0) < amount:
            return fail('INSUFFICIENT', 'Insufficient wallet balance')
        rec = request.env['res.partner'].sudo().search([
            '|', '|',
            ('email', '=ilike', recipient_q),
            ('phone', '=', recipient_q),
            ('mobile', '=', recipient_q),
        ], limit=1)
        if not rec:
            return fail('NOT_FOUND', 'Recipient not found', 404)
        if rec.id == partner.id:
            return fail('SELF', 'Cannot send to yourself', 400)
        Tx = request.env['uellow.customer.wallet.tx'].sudo()
        Tx.debit(partner, amount, tx_type='send',
                 description=note or f'Sent to {rec.name}',
                 counter_partner_id=rec.id)
        Tx.credit(rec, amount, tx_type='receive',
                  description=note or f'Received from {partner.name}',
                  counter_partner_id=partner.id)
        bal = float(getattr(partner, 'wallet_balance', 0) or 0)
        return ok({
            'sent':      fmt_price(amount),
            'balance':   fmt_price(bal),
            'recipient': {'name': rec.name, 'id': rec.id},
        })

    @http.route('/api/mobile/v2/wallet/lookup', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def lookup(self, **kw):
        """Verify a recipient before sending (for the UI)."""
        q = (kw.get('q') or '').strip()
        if not q:
            return fail('NO_QUERY', 'q is required')
        rec = request.env['res.partner'].sudo().search([
            '|', '|',
            ('email', '=ilike', q),
            ('phone', '=', q),
            ('mobile', '=', q),
        ], limit=1)
        if not rec:
            return fail('NOT_FOUND', 'No customer found', 404)
        return ok({
            'id':    rec.id,
            'name':  rec.name,
            'email': rec.email or '',
        })
