from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ReturnRequest(models.Model):
    _name = 'uellow.return.request'
    _description = 'Return Request'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(readonly=True, default='New')
    order_id = fields.Many2one('sale.order', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one(related='order_id.partner_id', store=True)
    order_line_id = fields.Many2one('sale.order.line', string='Product Line')
    product_id = fields.Many2one(related='order_line_id.product_id', store=True)

    reason = fields.Selection([
        ('defective',      'Defective / Damaged'),
        ('wrong_item',     'Wrong Item Received'),
        ('not_as_desc',    'Not as Described'),
        ('changed_mind',   'Changed Mind'),
        ('size_issue',     'Size / Fit Issue'),
        ('other',          'Other'),
    ], required=True, string='Return Reason')
    description = fields.Text('Customer Description')
    photo_ids = fields.Many2many('ir.attachment', string='Photos')

    state = fields.Selection([
        ('submitted',   'Submitted'),
        ('reviewing',   'Under Review'),
        ('approved',    'Approved'),
        ('rejected',    'Rejected'),
        ('received',    'Item Received'),
        ('refunded',    'Refunded'),
    ], default='submitted', tracking=True, index=True)

    refund_amount = fields.Float('Refund Amount')
    refund_method = fields.Selection([
        ('wallet', 'Store Wallet'), ('original', 'Original Payment'), ('voucher', 'Voucher'),
    ], default='wallet')
    admin_note = fields.Text('Admin Note')
    rejection_reason = fields.Text('Rejection Reason')
    stock_destination = fields.Selection([
        ('resell', 'Return to Stock'),
        ('vendor', 'Return to Vendor'),
        ('discard', 'Discard'),
    ], default='resell', string='Stock Destination')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.return.request') or 'New'
        records = super().create(vals_list)
        # Auto-approve small orders
        config = self.env['uellow.return.config'].get_config()
        for rec in records:
            if rec.order_id.amount_total <= config.auto_approve_threshold:
                rec.action_approve()
        return records

    def action_approve(self):
        config = self.env['uellow.return.config'].get_config()
        refund = self.order_line_id.price_total if self.order_line_id else self.order_id.amount_total
        fee = refund * config.restocking_fee_pct / 100
        self.write({
            'state': 'approved',
            'refund_amount': refund - fee,
            'refund_method': config.refund_method,
        })
        self.message_post(body=_('Return approved. Refund: %.3f KD') % self.refund_amount)

    def action_reject(self):
        self.state = 'rejected'

    def action_receive(self):
        self.state = 'received'

    def action_refund(self):
        self.state = 'refunded'
        # Credit wallet if applicable
        if self.refund_method == 'wallet' and self.partner_id:
            account = self.env['uellow.loyalty.account'].sudo().search([
                ('partner_id', '=', self.partner_id.id)
            ], limit=1) if 'uellow.loyalty.account' in self.env else False
            if account:
                account.earn_points(
                    int(self.refund_amount * 10),
                    reason=f'Return refund {self.name}',
                )
