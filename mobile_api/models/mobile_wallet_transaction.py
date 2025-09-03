# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MobileWalletTransaction(models.Model):
    _name = 'mobile.wallet.transaction'
    _description = 'Mobile Wallet Transaction'
    _rec_name = 'reference'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='User', required=True)
    amount = fields.Monetary(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    transaction_type = fields.Selection([
        ('credit', 'Credit'),
        ('debit', 'Debit')
    ], string='Transaction Type', required=True)
    description = fields.Text(string='Description')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', required=True)
    payment_method = fields.Char(string='Payment Method')
    reference = fields.Char(string='Reference', required=True)
    processed_date = fields.Datetime(string='Processed Date')

    @api.model
    def create(self, vals):
        if not vals.get('reference'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('mobile.wallet.transaction') or '/'
        return super().create(vals)
