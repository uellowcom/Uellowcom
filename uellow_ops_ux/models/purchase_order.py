from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_status = fields.Selection(
        selection=[
            ('no', 'No Bill'),
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        compute='_compute_payment_status',
        store=True,
        help='Aggregated payment state of this order\'s posted vendor bills.',
    )

    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.state',
                 'invoice_ids.move_type')
    def _compute_payment_status(self):
        for po in self:
            bills = po.invoice_ids.filtered(
                lambda m: m.move_type in ('in_invoice', 'in_refund')
                and m.state == 'posted')
            if not bills:
                po.payment_status = 'no'
                continue
            states = set(bills.mapped('payment_state'))
            if states <= {'paid', 'reversed'}:
                po.payment_status = 'paid'
            elif states <= {'in_payment', 'paid', 'reversed'}:
                po.payment_status = 'in_payment'
            elif 'partial' in states or (
                    ({'paid', 'in_payment', 'reversed'} & states) and 'not_paid' in states):
                po.payment_status = 'partial'
            else:
                po.payment_status = 'not_paid'
