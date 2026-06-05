# -*- coding: utf-8 -*-
"""Reviewers 2.0 — POINTS engine + purchase profit-share.

The old model paid a fixed KD price per session. Now:
  • Completing a session earns POINTS (per type, from Settings).
  • Points convert to KD wallet credit (rate + minimum in Settings) —
    the reviewer can withdraw the wallet or spend it at Uellow.
  • When the customer of a session BUYS the reviewed product and the
    order is DELIVERED, the reviewer earns a % of the sale (Settings:
    percent + window + basis price/margin) straight into his KD wallet.
Gap fixes: review_count now increments on COMPLETE (was on accept),
pending requests auto-expire by cron, complaint auto-suspend enforced.
"""
import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


def _icp(env, key, default):
    return env['ir.config_parameter'].sudo().get_param(
        'uellow_reviewers.' + key, default)


class ReviewerPoint(models.Model):
    _name = 'reviewer.point'
    _description = 'Reviewer points / earnings ledger'
    _order = 'create_date desc'

    reviewer_id = fields.Many2one('reviewer.profile', required=True,
                                  ondelete='cascade', index=True)
    points = fields.Integer(default=0,
        help='Signed: + for earnings, − for redemptions.')
    kd_amount = fields.Float(default=0.0,
        help='Signed KD movement (profit share / redemption credit).')
    source = fields.Selection([
        ('review_written', '✍️ Written review'),
        ('review_chat', '💬 Live chat'),
        ('review_photo', '📷 Photo review'),
        ('review_video', '🎥 Video call'),
        ('tryon_opinion', '🪞 Try-on opinion'),
        ('profit_share', '🛒 Purchase profit share'),
        ('redeem', '🔄 Points → wallet'),
        ('bonus', '🎁 Bonus'),
        ('adjustment', '✏️ Adjustment'),
    ], required=True, index=True)
    request_id = fields.Many2one('review.request', ondelete='set null')
    order_id = fields.Many2one('sale.order', ondelete='set null')
    note = fields.Char()


class ReviewerProfilePoints(models.Model):
    _inherit = 'reviewer.profile'

    point_ids = fields.One2many('reviewer.point', 'reviewer_id')
    points_balance = fields.Integer(compute='_compute_points', store=False)
    points_earned_total = fields.Integer(compute='_compute_points',
                                         store=False)
    profit_earned_total = fields.Float(compute='_compute_points',
                                       store=False,
                                       string='Profit share earned (KD)')

    def _compute_points(self):
        for r in self:
            pts = r.point_ids
            r.points_balance = sum(pts.mapped('points'))
            r.points_earned_total = sum(p.points for p in pts
                                        if p.points > 0)
            r.profit_earned_total = sum(p.kd_amount for p in pts
                                        if p.source == 'profit_share')

    def award_points(self, points, source, request=None, order=None,
                     note='', kd_amount=0.0):
        self.ensure_one()
        if not points and not kd_amount:
            return False
        return self.env['reviewer.point'].sudo().create({
            'reviewer_id': self.id,
            'points': int(points),
            'kd_amount': kd_amount,
            'source': source,
            'request_id': request.id if request else False,
            'order_id': order.id if order else False,
            'note': note,
        })

    def action_redeem_points(self, points=None):
        """Convert points → KD wallet credit (rate + min from Settings)."""
        self.ensure_one()
        rate = float(_icp(self.env, 'points_per_kd', '100') or 100)
        min_pts = int(float(_icp(self.env, 'min_redeem_points', '500')
                            or 500))
        pts = int(points or self.points_balance)
        if pts < min_pts:
            raise ValidationError(
                'Minimum redemption is %d points / الحد الأدنى للتحويل %d '
                'نقطة' % (min_pts, min_pts))
        if pts > self.points_balance:
            raise ValidationError(
                'Not enough points / لا تملك هذا العدد من النقاط')
        kd = round(pts / rate, 3)
        self.award_points(-pts, 'redeem', kd_amount=kd,
                          note='%d pts → %.3f KD' % (pts, kd))
        self.wallet_balance += kd
        self.total_earned += kd
        return kd

    # gap fix: complaints auto-suspend (the setting existed, nothing
    # enforced it)
    def write(self, vals):
        res = super().write(vals)
        if 'complaint_count' in vals:
            try:
                limit = int(float(_icp(self.env,
                                       'auto_suspend_complaints', '3')
                                  or 3))
                for r in self:
                    if limit > 0 and r.complaint_count >= limit \
                            and r.state == 'approved':
                        r.write({'state': 'suspended',
                                 'is_online': False})
            except Exception:
                pass
        return res


class ReviewRequestPoints(models.Model):
    _inherit = 'review.request'

    points_awarded = fields.Boolean(default=False)
    profit_credited = fields.Boolean(default=False)
    profit_amount = fields.Float(default=0.0,
                                 string='Profit share credited (KD)')
    profit_order_id = fields.Many2one('sale.order', ondelete='set null',
                                      string='Purchase order')

    def action_accept(self):
        res = super().action_accept()
        # gap fix: super() bumped review_count on ACCEPT — undo; the
        # count now belongs to COMPLETE.
        for r in self:
            if r.reviewer_id.review_count > 0:
                r.reviewer_id.review_count -= 1
        return res

    def action_complete(self, verdict=None, notes=None):
        res = super().action_complete(verdict=verdict, notes=notes)
        for r in self:
            r._award_completion_points()
            r.reviewer_id.review_count += 1
        return res

    def _award_completion_points(self):
        """POINTS per completed session (replaces the old fixed price)."""
        self.ensure_one()
        if self.points_awarded or not self.reviewer_id:
            return
        env = self.env
        if getattr(self, 'kind', '') == 'tryon_opinion':
            pts = int(float(_icp(env, 'points_tryon', '8') or 8))
            src = 'tryon_opinion'
        else:
            key = {'written': ('points_written', '10'),
                   'chat': ('points_chat', '15'),
                   'photo': ('points_photo', '12'),
                   'video': ('points_video', '20')}.get(
                       self.session_type, ('points_written', '10'))
            pts = int(float(_icp(env, key[0], key[1]) or key[1]))
            src = 'review_' + (self.session_type or 'written')
        if pts > 0:
            self.reviewer_id.award_points(pts, src, request=self,
                                          note=self.token)
            self.points_awarded = True

    # neutralize the OLD per-session money commission — purchases now pay
    # through the profit-share cron below, sessions pay POINTS only.
    def _calculate_commission(self):
        return

    # ── crons ────────────────────────────────────────────────────────
    @api.model
    def cron_expire_requests(self):
        """gap fix: pending/accepted requests past their expiry rotted in
        the queue forever — expire them so reviewers see a clean inbox."""
        now = fields.Datetime.now()
        # pending older than the configured request_expiry minutes
        try:
            ttl = int(float(_icp(self.env, 'request_expiry', '10') or 10))
        except Exception:
            ttl = 10
        stale_pending = self.search([
            ('state', '=', 'pending'),
            ('create_date', '<', now - timedelta(minutes=max(ttl, 1))),
        ])
        stale_pending.write({'state': 'expired'})
        # accepted sessions past expires_at
        overdue = self.search([
            ('state', 'in', ('accepted', 'active')),
            ('expires_at', '!=', False),
            ('expires_at', '<', now),
        ])
        overdue.write({'state': 'expired'})

    @api.model
    def cron_profit_share(self):
        """The session's customer BOUGHT the reviewed product and the
        order is DELIVERED → credit the reviewer % per Settings."""
        env = self.env
        try:
            pct = float(_icp(env, 'profit_share_pct', '3') or 3)
            window = int(float(_icp(env, 'profit_window_days', '7') or 7))
            basis = (_icp(env, 'profit_basis', 'price') or 'price').strip()
        except Exception:
            pct, window, basis = 3.0, 7, 'price'
        if pct <= 0:
            return
        sessions = self.search([
            ('state', '=', 'completed'),
            ('profit_credited', '=', False),
            ('customer_id', '!=', False),
            ('product_id', '!=', False),
            ('completed_at', '!=', False),
        ], limit=400)
        Sale = env['sale.order'].sudo()
        for s in sessions:
            horizon = s.completed_at + timedelta(days=window)
            if fields.Datetime.now() > horizon:
                # window closed with no purchase — stop re-scanning it
                s.profit_credited = True
                continue
            commercial = s.customer_id.commercial_partner_id \
                or s.customer_id
            orders = Sale.search([
                ('partner_id', 'child_of', commercial.id),
                ('state', 'in', ('sale', 'done')),
                ('date_order', '>=', s.completed_at),
                ('date_order', '<=', horizon),
            ], limit=10)
            for o in orders:
                if not self._order_delivered(o):
                    continue
                lines = o.order_line.filtered(
                    lambda l: l.product_id.product_tmpl_id.id ==
                    s.product_id.id and not l.display_type)
                if not lines:
                    continue
                base = sum(l.price_subtotal for l in lines)
                if basis == 'margin':
                    cost = sum((l.product_id.standard_price or 0.0)
                               * l.product_uom_qty for l in lines)
                    base = max(0.0, base - cost) or base
                amount = round(base * pct / 100.0, 3)
                if amount <= 0:
                    continue
                s.reviewer_id.award_points(
                    0, 'profit_share', request=s, order=o,
                    kd_amount=amount,
                    note='%s · %.1f%% of %.3f' % (o.name, pct, base))
                s.reviewer_id.wallet_balance += amount
                s.reviewer_id.total_earned += amount
                s.reviewer_id.purchase_count += 1
                s.write({'profit_credited': True,
                         'profit_amount': amount,
                         'profit_order_id': o.id})
                break

    @api.model
    def _order_delivered(self, so):
        try:
            if getattr(so, 'delivery_status', '') == 'delivered':
                return True
        except Exception:
            pass
        try:
            picks = so.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing')
            if picks and all(p.state == 'done' for p in picks):
                return True
        except Exception:
            pass
        return False


class ReviewerCommissionMethod(models.Model):
    _inherit = 'reviewer.commission'

    method = fields.Selection([
        ('bank', '🏦 Bank transfer'),
        ('knet', '💳 KNET'),
        ('wallet', '👛 Uellow wallet credit'),
    ], default='knet')
    details = fields.Char(help='IBAN / phone for the transfer.')

    def action_mark_paid(self):
        res = super().action_mark_paid()
        for p in self:
            if p.method == 'wallet':
                try:
                    Wallet = self.env.get('uellow.wallet')
                    if Wallet is not None:
                        Wallet.sudo().credit(
                            p.reviewer_id.partner_id, p.amount,
                            'Reviewer payout')
                except Exception:
                    pass
        return res


class ReviewerSettingsPoints(models.TransientModel):
    _inherit = 'reviewer.settings'

    # points per completed session
    points_written = fields.Integer('نقاط الرأي المكتوب', default=10)
    points_chat = fields.Integer('نقاط الشات المباشر', default=15)
    points_photo = fields.Integer('نقاط صورة + رأي', default=12)
    points_video = fields.Integer('نقاط مكالمة الفيديو', default=20)
    points_tryon = fields.Integer('نقاط رأي التراي-أون', default=8)
    # conversion
    points_per_kd = fields.Float('نقطة لكل 1 د.ك', default=100)
    min_redeem_points = fields.Integer('الحد الأدنى لتحويل النقاط',
                                       default=500)
    # profit share
    profit_share_pct = fields.Float('نسبة الريفيور من المبيعة %',
                                    default=3.0)
    profit_window_days = fields.Integer('نافذة احتساب الشراء (يوم)',
                                        default=7)
    profit_basis = fields.Selection([
        ('price', 'من قيمة البيع'),
        ('margin', 'من هامش الربح (سعر − تكلفة)'),
    ], default='price', string='أساس الحساب')

    _POINT_FIELDS = ['points_written', 'points_chat', 'points_photo',
                     'points_video', 'points_tryon', 'points_per_kd',
                     'min_redeem_points', 'profit_share_pct',
                     'profit_window_days', 'profit_basis']

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        for f in self._POINT_FIELDS:
            if f not in fields_list:
                continue
            raw = self._get_param(f, '')
            if not raw:
                continue
            fld = self._fields[f]
            try:
                if fld.type == 'integer':
                    res[f] = int(float(raw))
                elif fld.type == 'float':
                    res[f] = float(raw)
                else:
                    res[f] = raw
            except Exception:
                pass
        return res

    def execute(self):
        res = super().execute()
        for f in self._POINT_FIELDS:
            self._set_param(f, str(self[f]))
        return res
