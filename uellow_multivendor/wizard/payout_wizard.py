from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PayoutWizard(models.TransientModel):
    _name = 'uellow.payout.wizard'
    _description = 'Create Vendor Payout'

    vendor_id = fields.Many2one('uellow.vendor', required=True)
    available_balance = fields.Float(
        related='vendor_id.wallet_balance', string='Available Balance',
    )
    currency_id = fields.Many2one(
        related='vendor_id.currency_id',
    )
    amount = fields.Float('Payout Amount', required=True)
    payout_date = fields.Date('Payout Date', default=fields.Date.today)
    note = fields.Text('Notes')

    @api.onchange('vendor_id')
    def _onchange_vendor(self):
        if self.vendor_id:
            self.amount = self.vendor_id.wallet_balance

    def action_create_payout(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Amount must be positive.'))
        if self.amount > self.vendor_id.wallet_balance:
            raise UserError(_('Amount exceeds available balance.'))

        # Get released commission lines not yet in a payout
        lines = self.env['uellow.vendor.commission'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('state', '=', 'released'),
            ('payout_id', '=', False),
        ])
        payout = self.env['uellow.vendor.payout'].create({
            'vendor_id': self.vendor_id.id,
            'amount': self.amount,
            'payout_date': self.payout_date,
            'note': self.note or '',
            'commission_line_ids': [(6, 0, lines.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.vendor.payout',
            'view_mode': 'form',
            'res_id': payout.id,
        }
