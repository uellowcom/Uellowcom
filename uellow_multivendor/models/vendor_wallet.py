from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VendorWallet(models.Model):
    """
    Vendor wallet — tracks balance in vendor's preferred currency.
    All credits/debits go through wallet transaction lines.
    """
    _name = 'uellow.vendor.wallet'
    _description = 'Vendor Wallet'
    _rec_name = 'vendor_id'

    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.ref('base.KWD', raise_if_not_found=False),
    )
    balance = fields.Float(
        compute='_compute_balance', store=True, string='Balance',
    )
    pending_balance = fields.Float(
        compute='_compute_balance', store=True, string='Pending',
    )
    total_earned = fields.Float(
        compute='_compute_balance', store=True, string='Total Earned',
    )

    transaction_ids = fields.One2many(
        'uellow.wallet.transaction', 'wallet_id', string='Transactions',
    )

    min_payout = fields.Float('Minimum Payout Amount', default=20.0)
    payout_day = fields.Selection(
        [(str(i), str(i)) for i in range(1, 29)],
        default='1', string='Monthly Payout Day',
    )

    @api.depends('transaction_ids.amount', 'transaction_ids.state')
    def _compute_balance(self):
        for wallet in self:
            txns = wallet.transaction_ids
            wallet.total_earned = sum(
                t.amount for t in txns
                if t.tx_type == 'credit' and t.state == 'done'
            )
            paid_out = sum(
                t.amount for t in txns
                if t.tx_type == 'debit' and t.state == 'done'
            )
            wallet.balance = wallet.total_earned - paid_out
            wallet.pending_balance = sum(
                t.amount for t in txns
                if t.tx_type == 'credit' and t.state == 'pending'
            )

    def credit(self, amount, description='', commission_line_id=False):
        """Add funds to wallet."""
        self.ensure_one()
        if amount <= 0:
            return
        self.env['uellow.wallet.transaction'].create({
            'wallet_id': self.id,
            'amount': amount,
            'tx_type': 'credit',
            'description': description,
            'commission_line_id': commission_line_id or False,
            'state': 'done',
        })

    def debit(self, amount, description=''):
        """Remove funds from wallet (payout)."""
        self.ensure_one()
        if amount > self.balance:
            raise UserError(_('Insufficient wallet balance.'))
        self.env['uellow.wallet.transaction'].create({
            'wallet_id': self.id,
            'amount': amount,
            'tx_type': 'debit',
            'description': description,
            'state': 'done',
        })


class WalletTransaction(models.Model):
    """One debit or credit transaction on a vendor wallet."""
    _name = 'uellow.wallet.transaction'
    _description = 'Wallet Transaction'
    _order = 'id desc'

    wallet_id = fields.Many2one(
        'uellow.vendor.wallet', required=True, ondelete='cascade', index=True,
    )
    vendor_id = fields.Many2one(
        related='wallet_id.vendor_id', store=True,
    )
    currency_id = fields.Many2one(
        related='wallet_id.currency_id', store=True,
    )
    amount = fields.Float('Amount', required=True)
    tx_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit',  'Debit'),
    ], required=True, string='Type')
    description = fields.Char('Description')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done',    'Done'),
        ('failed',  'Failed'),
    ], default='done', string='Status')
    commission_line_id = fields.Many2one(
        'uellow.vendor.commission', string='Commission Line',
        ondelete='set null',
    )
    date = fields.Datetime(default=fields.Datetime.now, string='Date')
