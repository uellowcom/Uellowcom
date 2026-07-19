# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MobileWalletTransaction(models.Model):
    _name = 'mobile.wallet.transaction'
    _description = 'Mobile Wallet Transaction'
    _rec_name = 'reference'
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade'
    )
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    transaction_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ], string='Type', required=True)
    description = fields.Text('Description')
    reference = fields.Char('Reference', required=True)
    payment_method = fields.Char('Payment Method')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', required=True)
    processed_date = fields.Datetime('Processed Date')

    @api.model
    def create(self, vals):
        if not vals.get('reference'):
            vals['reference'] = (
                self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/'
            )
        return super().create(vals)

    def confirm_transaction(self):
        """Confirm and process the transaction"""
        self.ensure_one()
        if self.status != 'pending':
            raise ValidationError(_('Transaction is not pending'))
        if self.transaction_type == 'credit':
            self.partner_id.wallet_balance += self.amount
        else:
            if self.partner_id.wallet_balance < abs(self.amount):
                self.status = 'failed'
                return False
            self.partner_id.wallet_balance -= abs(self.amount)
        self.status = 'completed'
        self.processed_date = fields.Datetime.now()
        return True

    @api.model
    def create_topup_transaction(self, partner_id, amount, payment_method, reference=None):
        """Create a wallet top-up transaction"""
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))
        return self.create({
            'partner_id': partner_id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': f'Wallet top-up via {payment_method}',
            'payment_method': payment_method,
            'reference': reference or self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/',
            'status': 'pending',
        })

    @api.model
    def create_transfer_transaction(self, from_partner_id, to_partner_id, amount, note=None):
        """Create wallet transfer transactions"""
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))
        sender = self.env['res.partner'].browse(from_partner_id)
        if sender.wallet_balance < amount:
            raise ValidationError(_('Insufficient wallet balance'))
        seq = self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/'
        debit_txn = self.create({
            'partner_id': from_partner_id,
            'amount': -amount,
            'transaction_type': 'debit',
            'description': f'Transfer to user #{to_partner_id}' + (f': {note}' if note else ''),
            'reference': seq,
            'status': 'completed',
            'processed_date': fields.Datetime.now(),
        })
        credit_txn = self.create({
            'partner_id': to_partner_id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': f'Transfer from user #{from_partner_id}' + (f': {note}' if note else ''),
            'reference': seq,
            'status': 'completed',
            'processed_date': fields.Datetime.now(),
        })
        sender.wallet_balance -= amount
        receiver = self.env['res.partner'].browse(to_partner_id)
        receiver.wallet_balance += amount
        return {'debit_transaction': debit_txn.id, 'credit_transaction': credit_txn.id}

    @api.model
    def get_transaction_history(self, partner_id, limit=50, transaction_type=None):
        """Get transaction history for a partner"""
        domain = [('partner_id', '=', partner_id)]
        if transaction_type:
            domain.append(('transaction_type', '=', transaction_type))
        transactions = self.search(domain, limit=limit, order='create_date desc')
        result = []
        for txn in transactions:
            result.append({
                'id': txn.id,
                'amount': txn.amount,
                'type': txn.transaction_type,
                'description': txn.description,
                'reference': txn.reference,
                'payment_method': txn.payment_method,
                'status': txn.status,
                'date': txn.create_date.isoformat() if txn.create_date else None,
                'processed_date': txn.processed_date.isoformat() if txn.processed_date else None,
            })
        return result
