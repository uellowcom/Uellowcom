# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MobileWalletTransaction(models.Model):
    _name = 'mobile.wallet.transaction'
    _description = 'Mobile Wallet Transaction'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    amount = fields.Float('Amount', required=True)
    transaction_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ], string='Type', required=True)
    description = fields.Text('Description')
    reference = fields.Char('Reference')
    payment_method = fields.Char('Payment Method')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending')
    create_date = fields.Datetime('Transaction Date', default=fields.Datetime.now)
    processed_date = fields.Datetime('Processed Date')

    @api.model
    def create_topup_transaction(self, partner_id, amount, payment_method, reference=None):
        """Create a wallet top-up transaction"""
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))

        transaction = self.create({
            'partner_id': partner_id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': f'Wallet top-up via {payment_method}',
            'payment_method': payment_method,
            'reference': reference,
            'status': 'pending',
        })
        return transaction

    @api.model
    def create_transfer_transaction(self, from_partner_id, to_partner_id, amount, note=None):
        """Create wallet transfer transactions"""
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))

        # Check sender's balance
        sender = self.env['res.partner'].browse(from_partner_id)
        if sender.wallet_balance < amount:
            raise ValidationError(_('Insufficient wallet balance'))

        # Create debit transaction for sender
        debit_txn = self.create({
            'partner_id': from_partner_id,
            'amount': -amount,
            'transaction_type': 'debit',
            'description': f'Transfer to user #{to_partner_id}' + (f': {note}' if note else ''),
            'status': 'completed',
            'processed_date': fields.Datetime.now(),
        })

        # Create credit transaction for receiver
        credit_txn = self.create({
            'partner_id': to_partner_id,
            'amount': amount,
            'transaction_type': 'credit',
            'description': f'Transfer from user #{from_partner_id}' + (f': {note}' if note else ''),
            'status': 'completed',
            'processed_date': fields.Datetime.now(),
        })

        # Update balances
        sender.wallet_balance -= amount
        receiver = self.env['res.partner'].browse(to_partner_id)
        receiver.wallet_balance += amount

        return {'debit_transaction': debit_txn.id, 'credit_transaction': credit_txn.id}

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
                'date': txn.create_date.isoformat(),
                'processed_date': txn.processed_date.isoformat() if txn.processed_date else None,
            })
        return result


class ResPartnerWallet(models.Model):
    _inherit = 'res.partner'

    def get_wallet_balance(self):
        """Get current wallet balance"""
        self.ensure_one()
        return {
            'balance': self.wallet_balance,
            'currency': self.env.company.currency_id.name,
            'formatted_balance': f"{self.env.company.currency_id.symbol}{self.wallet_balance:.2f}",
        }

    def topup_wallet(self, amount, payment_method, reference=None):
        """Top up wallet balance"""
        self.ensure_one()
        if amount <= 0:
            raise ValidationError(_('Amount must be positive'))

        # Create transaction
        transaction = self.env['mobile.wallet.transaction'].create_topup_transaction(
            self.id, amount, payment_method, reference
        )

        # For demo purposes, auto-confirm the transaction
        # In production, this would be confirmed after payment gateway verification
        transaction.confirm_transaction()

        return {
            'transaction_id': transaction.id,
            'new_balance': self.wallet_balance,
            'status': 'completed'
        }

    def transfer_wallet_funds(self, recipient_identifier, amount, note=None):
        """Transfer funds to another user"""
        self.ensure_one()
        
        # Find recipient by email or phone
        recipient = self.env['res.partner'].search([
            '|',
            ('email', '=', recipient_identifier),
            ('mobile', '=', recipient_identifier)
        ], limit=1)

        if not recipient:
            raise ValidationError(_('Recipient not found'))

        if recipient.id == self.id:
            raise ValidationError(_('Cannot transfer to yourself'))

        # Create transfer transactions
        result = self.env['mobile.wallet.transaction'].create_transfer_transaction(
            self.id, recipient.id, amount, note
        )

        return {
            'transaction_ids': result,
            'sender_new_balance': self.wallet_balance,
            'recipient': {
                'name': recipient.name,
                'email': recipient.email,
            }
        }
