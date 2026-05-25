# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartnerWallet(models.Model):
    _inherit = 'res.partner'

    wallet_transaction_ids = fields.One2many(
        'mobile.wallet.transaction', 'partner_id', string='Wallet Transactions'
    )

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
        transaction = self.env['mobile.wallet.transaction'].create_topup_transaction(
            self.id, amount, payment_method, reference
        )
        transaction.confirm_transaction()
        return {
            'transaction_id': transaction.id,
            'new_balance': self.wallet_balance,
            'status': 'completed'
        }

    def transfer_wallet_funds(self, recipient_identifier, amount, note=None):
        """Transfer funds to another user"""
        self.ensure_one()
        recipient = self.env['res.partner'].search([
            '|',
            ('email', '=', recipient_identifier),
            ('mobile', '=', recipient_identifier)
        ], limit=1)
        if not recipient:
            raise ValidationError(_('Recipient not found'))
        if recipient.id == self.id:
            raise ValidationError(_('Cannot transfer to yourself'))
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
