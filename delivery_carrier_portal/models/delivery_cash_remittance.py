# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
import io


class DeliveryCashRemittance(models.Model):
    _name = 'delivery.cash.remittance'
    _description = 'Delivery Cash Remittance'
    _inherit = ['mail.thread']
    _studio = False
    _mail_activity_res_model = False
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('delivery.cash.remittance'))
    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Carrier Company', required=True,
    )
    settlement_mode = fields.Selection([
        ('per_order', 'Per Order'),
        ('weekly',    'Weekly'),
        ('monthly',   'Monthly'),
    ], string='Settlement Mode', default='per_order', required=True)

    order_ids = fields.Many2many(
        'sale.order', 'remittance_order_rel', 'remittance_id', 'order_id',
        string='Orders',
    )
    line_ids = fields.One2many(
        'delivery.cash.remittance.line', 'remittance_id', string='Order Lines',
    )
    total_amount           = fields.Float(compute='_compute_totals', string='Total Amount (KD)',      store=True, digits=(10,3))
    total_delivery_fees    = fields.Float(compute='_compute_totals', string='Delivery Fees',          store=True, digits=(10,3))
    total_cash_commission  = fields.Float(compute='_compute_totals', string='Cash Commission',        store=True, digits=(10,3))
    total_cancel_fees      = fields.Float(compute='_compute_totals', string='Cancel Fees',            store=True, digits=(10,3))
    total_return_exch_fees = fields.Float(compute='_compute_totals', string='Return/Exchange Fees',   store=True, digits=(10,3))
    total_carrier_cost     = fields.Float(compute='_compute_totals', string='Total Carrier Cost',     store=True, digits=(10,3))
    cash_collected         = fields.Float(compute='_compute_totals', string='Cash Collected',         store=True, digits=(10,3))
    net_to_uellow          = fields.Float(compute='_compute_totals', string='Net to Uellow',          store=True, digits=(10,3))

    state = fields.Selection([
        ('draft',    'Draft'),
        ('pending',  'Pending Approval'),
        ('partial',  'Partial'),
        ('remitted', 'Remitted'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    remittance_date = fields.Date(string='Remittance Date')
    reference_no = fields.Char(string='Bank Reference')
    notes = fields.Text(string='Notes')
    rejection_reason = fields.Text(string='Rejection Reason')
    carrier_ref = fields.Char(string='Carrier Reference', help='Reference number provided by the carrier company for this settlement')

    @api.depends('line_ids', 'line_ids.order_id', 'order_ids')
    def _compute_totals(self):
        for rec in self:
            if rec.line_ids:
                lines = rec.line_ids
                rec.total_amount           = sum(l.amount for l in lines)
                rec.total_delivery_fees    = sum((l.order_id.carrier_delivery_fee   or 0) for l in lines if l.order_id)
                rec.total_cash_commission  = sum((l.order_id.carrier_cash_commission or 0) for l in lines if l.order_id)
                rec.total_cancel_fees      = sum((l.order_id.carrier_cancel_fee     or 0) for l in lines if l.order_id)
                rec.total_return_exch_fees = sum((l.order_id.carrier_return_fee     or 0) for l in lines if l.order_id)
                rec.total_carrier_cost     = (rec.total_delivery_fees + rec.total_cash_commission +
                                              rec.total_cancel_fees + rec.total_return_exch_fees)
                rec.cash_collected         = sum((l.order_id.amount_total or 0) for l in lines
                                                 if l.order_id and l.order_id.payment_method_type == 'cash'
                                                 and l.order_id.delivery_status == 'delivered')
                rec.net_to_uellow = rec.cash_collected - rec.total_carrier_cost
            else:
                rec.total_amount           = sum(rec.order_ids.mapped('amount_total'))
                rec.total_delivery_fees    = rec.total_cash_commission = 0.0
                rec.total_cancel_fees      = rec.total_return_exch_fees = 0.0
                rec.total_carrier_cost     = rec.cash_collected = rec.net_to_uellow = 0.0

                rec.total_amount = sum(rec.order_ids.mapped('amount_total'))


    def get_barcode_base64(self):
        """Generate Code128 barcode as base64 PNG using Odoo built-in tools."""
        try:
            from odoo.tools.barcode import get_barcode_svg
            svg = get_barcode_svg(self.name or '', barcode_type='Code128')
            return base64.b64encode(svg.encode('utf-8')).decode('utf-8')
        except Exception:
            try:
                # Fallback: use reportlab
                from reportlab.graphics.barcode import code128
                from reportlab.graphics.shapes import Drawing
                from reportlab.graphics import renderPM
                barcode = code128.Code128(self.name or '', barHeight=30, barWidth=1.0)
                d = Drawing(barcode.width + 10, 40)
                d.add(barcode)
                buffer = io.BytesIO()
                renderPM.drawToFile(d, buffer, fmt='PNG')
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
            except Exception:
                return ''

    def action_submit(self):
        """Carrier submits remittance request."""
        self.write({'state': 'pending'})

    def action_approve_all(self):
        """Uellow approves all lines."""
        for line in self.line_ids:
            line.write({'approval_state': 'approved'})
        self.write({'state': 'remitted', 'remittance_date': fields.Date.today()})
        for line in self.line_ids:
            if line.order_id:
                line.order_id.cash_collection_status = 'remitted'

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_remitted(self):
        self.write({'state': 'remitted', 'remittance_date': fields.Date.today()})
        for line in self.line_ids:
            if line.order_id:
                line.order_id.cash_collection_status = 'remitted'


class DeliveryCashRemittanceLine(models.Model):
    _name = 'delivery.cash.remittance.line'
    _description = 'Remittance Order Line'

    remittance_id = fields.Many2one('delivery.cash.remittance', ondelete='cascade')
    order_id = fields.Many2one('sale.order', string='Order')
    order_name = fields.Char(related='order_id.name', string='Order #')
    carrier_order_ref = fields.Char(related='order_id.carrier_order_ref', string='Carrier Order Ref')
    amount = fields.Float(string='Amount (KD)', digits=(10, 3))
    delivery_status = fields.Selection(related='order_id.delivery_status', string='Delivery Status')
    return_status = fields.Selection(related='order_id.return_status', string='Return Status')
    approval_state = fields.Selection([
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('noted',    'Approved w/ Note'),
        ('rejected', 'Rejected'),
    ], default='pending', string='Uellow Approval')
    uellow_notes = fields.Char(string='Uellow Notes')

    def action_approve(self):
        self.write({'approval_state': 'approved'})
        self._check_remittance_complete()

    def action_approve_with_note(self):
        self.write({'approval_state': 'noted'})
        self._check_remittance_complete()

    def action_reject_line(self):
        self.write({'approval_state': 'rejected'})

    def _check_remittance_complete(self):
        rem = self.remittance_id
        if rem and all(l.approval_state in ('approved', 'noted', 'rejected')
                       for l in rem.line_ids):
            approved = rem.line_ids.filtered(
                lambda l: l.approval_state in ('approved', 'noted'))
            if approved:
                rem.write({'state': 'remitted' if len(approved) == len(rem.line_ids) else 'partial',
                           'remittance_date': fields.Date.today()})
                for line in approved:
                    if line.order_id:
                        line.order_id.cash_collection_status = 'remitted'
