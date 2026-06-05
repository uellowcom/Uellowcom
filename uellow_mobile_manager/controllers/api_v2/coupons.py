"""
Coupons — /api/mobile/v2/coupons*

list    GET  /                → user's available coupons + ongoing promotions

Coupon source:
  • `loyalty.card` rows linked to this partner that are still valid
    (expiration_date >= today, points_balance > 0 OR no points concept).
  • Programs of type=='promotion' / 'promo_code' that are website_published
    and currently active — surfaced as "available codes" so the user can
    discover them in-app.

Each coupon record returned carries everything the dialog needs to show
without a second round-trip: code, description, discount, min cart,
expiry, terms, category, isUsable now, etc.
"""
from datetime import date

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, current_partner, require_auth, bilingual,
)


def _program_dict(prog):
    """Serialize a loyalty.program row as a coupon listing card."""
    discount = ''
    if prog.reward_ids:
        r = prog.reward_ids[0]
        if r.reward_type == 'shipping':
            discount = 'FREE SHIPPING'
        elif r.discount_mode == 'percent':
            discount = f"{int(r.discount)}% OFF"
        elif r.discount_mode == 'per_order':
            discount = f"{int(r.discount)} OFF"
        elif r.reward_type == 'product':
            discount = (r.reward_product_id.name or 'Free product') if r.reward_product_id else 'Free product'
    min_amt = 0.0
    if prog.rule_ids:
        min_amt = sum(prog.rule_ids.mapped('minimum_amount')) or 0
    # v2.1.51 — surface the actual promo code (lives on the RULE, not the
    # program) so the app's "apply" button has something to send.
    code = ''
    if prog.program_type == 'promo_code' and prog.rule_ids:
        codes = [c for c in prog.rule_ids.mapped('code') if c]
        code = codes[0] if codes else ''
    auto = prog.trigger == 'auto' if hasattr(prog, 'trigger') else not code
    if code:
        terms = {'en': f'Code: {code} — apply it at checkout.',
                 'ar': f'الكود: {code} — طبّقه عند الدفع.'}
    elif auto:
        terms = {'en': 'Auto-applied on eligible orders.',
                 'ar': 'يُطبق تلقائياً على الطلبات المؤهلة.'}
    else:
        terms = {'en': 'Requires a coupon code sent to you.',
                 'ar': 'يتطلب كود كوبون مُرسل إليك.'}
    if min_amt:
        terms = {'en': terms['en'] + f' Min. order: {min_amt:g}.',
                 'ar': terms['ar'] + f' أقل طلب: {min_amt:g}.'}
    return {
        'id':            prog.id,
        'kind':          'program',
        'name':          bilingual(prog, 'name'),
        'discount_text': discount or '—',
        'min_amount':    min_amt,
        'currency':      prog.currency_id.symbol if prog.currency_id else 'KD',
        'expiry':        prog.date_to and prog.date_to.isoformat() or None,
        'code':          code,
        'is_auto':       bool(auto and not code),
        'terms':         terms,
        'category': 'promotion',
        'usable_now': True,
        'color': '#F5C320',
    }


def _card_dict(card):
    """Serialize a loyalty.card (an actual issued coupon/gift card)."""
    prog = card.program_id
    discount = ''
    if prog.reward_ids:
        r = prog.reward_ids[0]
        if r.discount_mode == 'percent':
            discount = f"{int(r.discount)}% OFF"
        elif r.discount_mode == 'per_order':
            discount = f"{card.points} {prog.currency_id.symbol or 'KD'} OFF"
    color_map = {
        'gift_card':  '#10B981',
        'ewallet':    '#0EA5E9',
        'coupons':    '#F5C320',
        'promotion':  '#FFA500',
        'promo_code': '#8B5CF6',
    }
    return {
        'id':            card.id,
        'kind':          'card',
        'program_kind':  prog.program_type,
        'name':          bilingual(prog, 'name'),
        'discount_text': discount or '—',
        'min_amount':    sum(prog.rule_ids.mapped('minimum_amount')) if prog.rule_ids else 0.0,
        'currency':      prog.currency_id.symbol if prog.currency_id else 'KD',
        'expiry':        card.expiration_date and card.expiration_date.isoformat() or None,
        'code':          card.code or '',
        'terms': {
            'en': f"Code: {card.code}" if card.code else 'Use at checkout.',
            'ar': f"الكود: {card.code}" if card.code else 'استخدمه عند الدفع.',
        },
        'category': prog.program_type,
        'usable_now': (card.expiration_date is False
                       or card.expiration_date >= date.today()),
        'color': color_map.get(prog.program_type, '#F5C320'),
        'balance': card.points,
    }


class MobileCouponsAPI(http.Controller):

    @http.route('/api/mobile/v2/coupons', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_coupons(self, **kw):
        partner = current_partner()
        out = []

        # 1) Customer-bound coupons (loyalty.card rows).
        cards = request.env['loyalty.card'].sudo().search([
            ('partner_id', '=', partner.id),
            '|', ('expiration_date', '=', False),
                 ('expiration_date', '>=', date.today()),
        ], order='expiration_date asc')
        for c in cards:
            out.append(_card_dict(c))

        # 2) Public promotion programs the user can self-claim.
        # v2.1.51 — website-scoped, must HAVE a reward, and promo-code
        # programs now carry their actual code so the app can apply them
        # (codeless cards were the "coupon never applies" complaint).
        from ._common import get_website
        wid = None
        try:
            wid = get_website().id
        except Exception:
            pass
        dom = [
            ('active', '=', True),
            ('program_type', 'in', ['promotion', 'promo_code', 'coupons']),
            '|', ('date_to', '=', False), ('date_to', '>=', date.today()),
        ]
        if wid:
            dom = ['|', ('website_id', '=', False),
                   ('website_id', '=', wid)] + dom
        programs = request.env['loyalty.program'].sudo().search(dom)
        seen = {c['name']['en'] for c in out if c.get('name')}
        for p in programs:
            if not p.reward_ids:
                continue                      # nothing to grant — hide
            d = _program_dict(p)
            # v2.1.56 — a program with NO typable code that is NOT
            # auto-applied (e.g. type 'coupons' awaiting issued cards) is
            # not actionable from the app; listing it produced the
            # contradictory "requires a mailed code" + "auto-applied"
            # labels. The customer's own issued cards already show above.
            if not d['code'] and not d['is_auto']:
                continue
            if d['name']['en'] in seen:
                continue
            out.append(d)
        return ok(out)
