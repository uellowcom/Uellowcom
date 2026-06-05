# -*- coding: utf-8 -*-
# Uellow Wallet — a simple ledger on res.partner. Each row is a credit
# (top-up, refund, gift-card redemption, send-from-friend) or debit
# (spent-on-order, send-to-friend). wallet_balance is computed.
#
# Designed to play nice with Odoo's standard sale.order flow: when an
# order is paid using wallet, we record a 'spend' transaction. Refunds
# from cancelled orders go back as a 'refund' credit.
from odoo import models, fields, api


class UellowWalletTransaction(models.Model):
    _name = 'uellow.customer.wallet.tx'
    _description = 'Wallet Transaction'
    _order = 'id desc'

    partner_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade', index=True,
    )
    amount = fields.Float('Amount', required=True,
        help='Positive for credit, negative for debit')
    transaction_type = fields.Selection([
        ('topup',       'Top-up'),
        ('spend',       'Spent on Order'),
        ('refund',      'Order Refund'),
        ('gift_card',   'Gift Card Redeemed'),
        ('send',        'Sent to Friend'),
        ('receive',     'Received from Friend'),
        ('cashback',    'Cashback'),
        ('adjust',      'Manual Adjustment'),
    ], required=True, default='topup')
    state = fields.Selection([
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('reversed',  'Reversed'),
    ], default='completed', required=True)
    description = fields.Char('Description', default='')
    reference = fields.Char('Reference / Code', index=True)
    order_id = fields.Many2one('sale.order', ondelete='set null')
    counter_partner_id = fields.Many2one(
        'res.partner', ondelete='set null',
        string='Counterparty (send/receive)',
    )

    @api.model
    def credit(self, partner, amount, tx_type='topup', description='', reference=None,
               order_id=None, counter_partner_id=None):
        if amount <= 0 or not partner:
            return self.browse()
        tx = self.create({
            'partner_id': partner.id,
            'amount': abs(amount),
            'transaction_type': tx_type,
            'description': description or '',
            'reference': reference,
            'order_id': order_id,
            'counter_partner_id': counter_partner_id,
        })
        # v2.1.62 — wallet-credit event notification (admin-toggleable)
        try:
            cur = self.env.company.currency_id
            self.env['mobile.customer.notification'].push_event(
                partner, 'wallet_credit',
                '+%.3f %s added to your wallet 💰' % (abs(amount), cur.name),
                'تمت إضافة %.3f %s إلى محفظتك 💰' % (abs(amount), cur.name),
                description or '', description or '',
                {'type': 'screen', 'value': 'wallet'})
        except Exception:
            pass
        return tx

    @api.model
    def debit(self, partner, amount, tx_type='spend', description='', reference=None,
              order_id=None, counter_partner_id=None):
        if amount <= 0 or not partner:
            return self.browse()
        if float(getattr(partner, 'wallet_balance', 0) or 0) < abs(amount):
            from odoo.exceptions import UserError
            from odoo import _
            raise UserError(_('Insufficient wallet balance.'))
        return self.create({
            'partner_id': partner.id,
            'amount': -abs(amount),
            'transaction_type': tx_type,
            'description': description or '',
            'reference': reference,
            'order_id': order_id,
            'counter_partner_id': counter_partner_id,
        })


class ResPartnerWallet(models.Model):
    _inherit = 'res.partner'

    wallet_balance = fields.Float(
        'Wallet Balance', compute='_compute_wallet_balance', store=False,
    )
    wallet_transaction_ids = fields.One2many(
        'uellow.customer.wallet.tx', 'partner_id',
        string='Wallet Transactions',
    )

    @api.depends('wallet_transaction_ids.amount',
                 'wallet_transaction_ids.state')
    def _compute_wallet_balance(self):
        # v2.1.70 — the missing @api.depends made the cached balance go
        # STALE within a request: /wallet/send debited correctly but
        # returned the pre-send balance to the app.
        # Cheap aggregation — read_group keeps this fast even with many txs.
        if not self:
            return
        Tx = self.env['uellow.customer.wallet.tx'].sudo()
        rows = Tx.read_group(
            domain=[('partner_id', 'in', self.ids),
                    ('state', '=', 'completed')],
            fields=['amount:sum'],
            groupby=['partner_id'],
        )
        bal_map = {r['partner_id'][0]: r['amount'] for r in rows if r.get('partner_id')}
        for p in self:
            p.wallet_balance = bal_map.get(p.id, 0.0)
