"""Account tab aggregate — /api/mobile/v2/account/*

Returns everything the Account tab needs in ONE call so the screen
opens instantly (no skeleton flicker):
  • user profile
  • loyalty card (points / tier / next-tier progress)
  • wallet balance + recent activity
  • addresses count
  • orders count + most-recent state
  • notification unread count
  • feature tiles for shipping / preferences / reviews / wishlist
"""
from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, ok, fail, current_partner, require_auth, fmt_price,
    img_url, bilingual,
)
from .auth import _serialize_user, _loyalty_points
from .loyalty import _next_tier, _progress_pct


class MobileAccountAPI(http.Controller):

    @http.route('/api/mobile/v2/account/overview', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def overview(self, **kw):
        partner = current_partner()
        env = request.env

        # ── Loyalty
        cards = env['loyalty.card'].sudo().search([('partner_id', '=', partner.id)])
        points = int(sum(cards.mapped('points')))
        Prog = env.get('uellow.loyalty.program')
        thresholds = {'silver': 1000, 'gold': 5000, 'platinum': 15000}
        redeem_rate = 100
        if Prog is not None:
            prog = Prog.sudo().search([], limit=1)
            if prog:
                thresholds = {
                    'silver':   int(getattr(prog, 'tier_silver_min', 1000)),
                    'gold':     int(getattr(prog, 'tier_gold_min', 5000)),
                    'platinum': int(getattr(prog, 'tier_platinum_min', 15000)),
                }
                redeem_rate = int(getattr(prog, 'points_per_kd_redeem', 100))
        tier = 'bronze'
        if points >= thresholds['platinum']: tier = 'platinum'
        elif points >= thresholds['gold']: tier = 'gold'
        elif points >= thresholds['silver']: tier = 'silver'
        next_t, next_thr = _next_tier(tier, thresholds)
        kd_value = round(points / redeem_rate, 3) if redeem_rate else 0

        # ── Wallet
        wallet_balance = float(getattr(partner, 'wallet_balance', 0) or 0)
        Wal = env.get('uellow.wallet.transaction')
        last_tx = []
        # uellow.wallet.transaction is the VENDOR-side wallet; it has
        # `wallet_id` not `partner_id`. Skip it for customer accounts —
        # the customer-facing balance lives on res.partner.wallet_balance.
        if Wal is not None and 'partner_id' in Wal._fields:
            txs = Wal.sudo().search([
                ('partner_id', '=', partner.id),
            ], order='create_date desc', limit=3)
            for t in txs:
                last_tx.append({
                    'amount': fmt_price(t.amount),
                    'type': getattr(t, 'transaction_type', '') or '',
                    'date': t.create_date.isoformat() if t.create_date else None,
                    'description': getattr(t, 'description', '') or '',
                })

        # ── Orders + addresses + notifs counts
        Order = env['sale.order'].sudo()
        order_count = Order.search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ])
        in_progress = Order.search_count([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale']),
        ])
        # v2.1.88 — per-status counts for the account "My Orders" grid badges.
        status_counts = {'draft': 0, 'confirmed': 0, 'preparing': 0,
                         'shipping': 0, 'delivered': 0}
        try:
            from .orders import _uellow_status
            for o in Order.search([('partner_id', '=', partner.id),
                                   ('state', '!=', 'cancel')], limit=200):
                # _uellow_status returns a dict — key on its 'code' (v2.1.92 fix:
                # was comparing the whole dict, so all counts stayed 0).
                st = _uellow_status(o)['code']
                if st in status_counts:
                    status_counts[st] += 1
        except Exception:
            pass
        recent_order = Order.search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
        ], order='date_order desc', limit=1)
        recent_order_dict = None
        if recent_order:
            # v2.1.94 — the REAL unified status: the card used to get only
            # the raw sale state ('sale'), so its progress sat at
            # "confirmed" (blue) forever, even after delivery.
            try:
                from .orders import _uellow_status
                u_code = _uellow_status(recent_order)['code']
            except Exception:
                u_code = 'confirmed'
            recent_order_dict = {
                'id': recent_order.id,
                'name': recent_order.name,
                'state': recent_order.state,
                'uellow_status': u_code,
                'total': fmt_price(recent_order.amount_total, recent_order.currency_id),
                'date': recent_order.date_order.isoformat() if recent_order.date_order else None,
            }
        addr_count = env['res.partner'].sudo().search_count([
            ('parent_id', '=', partner.id),
            ('type', 'in', ('delivery', 'invoice')),
        ])
        # Unread notifications
        Notif = env.get('mobile.notification')
        unread = 0
        if Notif is not None and 'is_read' in Notif._fields:
            unread = Notif.sudo().search_count([
                ('partner_id', '=', partner.id), ('is_read', '=', False),
            ])

        # ── Banners (loyalty + wallet, ready-to-render)
        banners = [
            {
                'kind': 'loyalty',
                'title': {'en': 'Loyalty Points', 'ar': 'نقاط الولاء'},
                'subtitle': {
                    'en': f'{points:,} pts  =  {kd_value:.3f} KD',
                    'ar': f'{points:,} نقطة  =  {kd_value:.3f} د.ك',
                },
                'tier': tier,
                'tier_label': {
                    'bronze':   {'en': 'Bronze',   'ar': 'برونزي'},
                    'silver':   {'en': 'Silver',   'ar': 'فضي'},
                    'gold':     {'en': 'Gold',     'ar': 'ذهبي'},
                    'platinum': {'en': 'Platinum', 'ar': 'بلاتيني'},
                }[tier],
                'progress_pct': _progress_pct(points, tier, thresholds),
                'next_tier':       next_t,
                'next_threshold':  next_thr,
                'gradient_from':   '#FFD340',
                'gradient_to':     '#F5A800',
                'cta': {'en': 'Use points', 'ar': 'استبدل النقاط'},
            },
            {
                'kind': 'wallet',
                'title': {'en': 'Uellow Wallet', 'ar': 'محفظة Uellow'},
                'subtitle': {
                    'en': f'Balance: {wallet_balance:.3f} KD',
                    'ar': f'الرصيد: {wallet_balance:.3f} د.ك',
                },
                'balance': fmt_price(wallet_balance),
                'recent': last_tx,
                'gradient_from':   '#412402',
                'gradient_to':     '#1F1100',
                'cta': {'en': 'Top up', 'ar': 'شحن'},
            },
        ]

        # ── Quick-access tiles (cards under the banners)
        tiles = [
            _tile('orders',        'Orders',         'الطلبات',       count=order_count),
            _tile('wishlist',      'Wishlist',       'المفضلة'),
            _tile('addresses',     'Addresses',      'العناوين',     count=addr_count),
            _tile('shipping',      'Shipping',       'الشحن'),
            _tile('reviews',       'My Reviews',     'مراجعاتي'),
            _tile('notifications', 'Notifications',  'الإشعارات',     count=unread, highlight=unread > 0),
            _tile('support',       'Support',        'الدعم'),
            _tile('settings',      'Settings',       'الإعدادات'),
        ]

        # v2.2.10 — admin console gate (small shield icon in حسابي)
        try:
            from .admin_app import is_admin_partner
            is_admin = is_admin_partner(partner)
        except Exception:
            is_admin = False

        return ok({
            'user': _serialize_user(partner),
            'is_admin': is_admin,
            'banners': banners,
            'tiles': tiles,
            'stats': {
                'orders_total': order_count,
                'orders_in_progress': in_progress,
                'status_counts': status_counts,
                'addresses_count': addr_count,
                'notifications_unread': unread,
                'points': points,
                'wallet_balance': fmt_price(wallet_balance),
            },
            'recent_order': recent_order_dict,
        })


def _tile(key, en, ar, *, count=None, highlight=False):
    return {
        'key': key,
        'label': {'en': en, 'ar': ar},
        'count': count,
        'highlight': highlight,
    }
