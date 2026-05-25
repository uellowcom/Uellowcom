from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class LoyaltyAccount(models.Model):
    """
    One loyalty account per customer (res.partner).
    Tracks balance, tier, total earned/redeemed.
    """
    _name = 'uellow.loyalty.account'
    _description = 'Customer Loyalty Account'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade', index=True,
    )
    balance = fields.Integer(
        compute='_compute_balance', store=True, string='Point Balance',
    )
    total_earned = fields.Integer('Total Earned', default=0)
    total_redeemed = fields.Integer('Total Redeemed', default=0)
    total_expired = fields.Integer('Total Expired', default=0)

    tier = fields.Selection([
        ('bronze',   'Bronze'),
        ('silver',   'Silver'),
        ('gold',     'Gold'),
        ('platinum', 'Platinum'),
    ], default='bronze', compute='_compute_tier', store=True)

    lifetime_points = fields.Integer('Lifetime Points Earned', default=0)

    transaction_ids = fields.One2many(
        'uellow.loyalty.transaction', 'account_id', string='Transactions',
    )

    _sql_constraints = [
        ('unique_partner', 'UNIQUE(partner_id)',
         'Customer already has a loyalty account.'),
    ]

    @api.depends('transaction_ids.points', 'transaction_ids.state')
    def _compute_balance(self):
        for acc in self:
            earned = sum(
                t.points for t in acc.transaction_ids
                if t.tx_type == 'earn' and t.state == 'active'
            )
            spent = sum(
                t.points for t in acc.transaction_ids
                if t.tx_type in ('redeem', 'expire') and t.state == 'active'
            )
            acc.balance = max(0, earned - spent)

    @api.depends('lifetime_points')
    def _compute_tier(self):
        program = self.env['uellow.loyalty.program'].get_program()
        for acc in self:
            pts = acc.lifetime_points
            if pts >= program.tier_platinum_min:
                acc.tier = 'platinum'
            elif pts >= program.tier_gold_min:
                acc.tier = 'gold'
            elif pts >= program.tier_silver_min:
                acc.tier = 'silver'
            else:
                acc.tier = 'bronze'

    @api.model
    def get_or_create(self, partner):
        acc = self.search([('partner_id', '=', partner.id)], limit=1)
        if not acc:
            acc = self.create({'partner_id': partner.id})
        return acc

    def earn_points(self, points, reason='', order_id=False):
        """Add points to account."""
        self.ensure_one()
        if points <= 0:
            return
        program = self.env['uellow.loyalty.program'].get_program()
        # Apply tier multiplier
        multipliers = {
            'silver': program.silver_multiplier,
            'gold': program.gold_multiplier,
            'platinum': program.platinum_multiplier,
        }
        multiplier = multipliers.get(self.tier, 1.0)
        final_points = int(points * multiplier)

        expire_date = False
        if program.points_expire_days > 0:
            expire_date = fields.Date.today() + timedelta(
                days=program.points_expire_days)

        self.env['uellow.loyalty.transaction'].create({
            'account_id': self.id,
            'points': final_points,
            'tx_type': 'earn',
            'reason': reason,
            'order_id': order_id or False,
            'expire_date': expire_date,
            'state': 'active',
        })
        self.lifetime_points += final_points
        self.total_earned += final_points

    def redeem_points(self, points, order_id=False):
        """Redeem points for a discount."""
        self.ensure_one()
        program = self.env['uellow.loyalty.program'].get_program()
        if points < program.min_points_redeem:
            raise UserError(_(
                'Minimum redemption is %d points.') % program.min_points_redeem)
        if points > self.balance:
            raise UserError(_('Insufficient points balance.'))
        discount_amount = points / program.points_per_kd_redeem
        self.env['uellow.loyalty.transaction'].create({
            'account_id': self.id,
            'points': points,
            'tx_type': 'redeem',
            'reason': f'Redeemed on order',
            'order_id': order_id or False,
            'state': 'active',
        })
        self.total_redeemed += points
        return discount_amount

    @api.model
    def cron_expire_points(self):
        """Daily cron: expire old points."""
        today = fields.Date.today()
        expired_txns = self.env['uellow.loyalty.transaction'].search([
            ('expire_date', '<=', today),
            ('tx_type', '=', 'earn'),
            ('state', '=', 'active'),
        ])
        for txn in expired_txns:
            txn.state = 'expired'
            txn.account_id.total_expired += txn.points


class LoyaltyTransaction(models.Model):
    """One credit or debit on a loyalty account."""
    _name = 'uellow.loyalty.transaction'
    _description = 'Loyalty Transaction'
    _order = 'id desc'

    account_id = fields.Many2one(
        'uellow.loyalty.account', required=True, ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        related='account_id.partner_id', store=True,
    )
    points = fields.Integer('Points', required=True)
    tx_type = fields.Selection([
        ('earn',    'Earned'),
        ('redeem',  'Redeemed'),
        ('expire',  'Expired'),
        ('adjust',  'Manual Adjustment'),
    ], required=True, string='Type')
    reason = fields.Char('Reason')
    order_id = fields.Many2one('sale.order', ondelete='set null')
    expire_date = fields.Date('Expires On')
    state = fields.Selection([
        ('active',  'Active'),
        ('expired', 'Expired'),
    ], default='active')
    date = fields.Datetime(default=fields.Datetime.now)
