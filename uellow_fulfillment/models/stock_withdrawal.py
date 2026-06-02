from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockWithdrawal(models.Model):
    _name = 'uellow.stock.withdrawal'
    _description = 'Vendor Stock Withdrawal / Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char('Reference', required=True, copy=False, readonly=True, default='New')
    vendor_location_id = fields.Many2one(
        'uellow.vendor.location', string='Vendor Sub-warehouse',
        required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one(
        related='vendor_location_id.partner_id', string='Vendor', store=True, readonly=True)
    location_id = fields.Many2one(
        related='vendor_location_id.location_id', string='Source Location', store=True, readonly=True)

    initiated_by = fields.Selection([
        ('vendor', 'Vendor'),
        ('uellow', 'Uellow'),
    ], string='Initiated By', default='vendor', required=True, index=True)

    reason = fields.Selection([
        ('slow_moving', 'Slow-moving stock'),
        ('sell_elsewhere', 'Sell elsewhere'),
        ('quality', 'Quality issue'),
        ('expired', 'Expired / near expiry'),
        ('contract_end', 'Contract ended'),
        ('other', 'Other'),
    ], string='Reason', required=True)
    reason_note = fields.Text('Reason Note')
    admin_note = fields.Text('Admin Note')

    destination = fields.Selection([
        ('vendor', 'Return to Vendor'),
        ('scrap', 'Scrap / Discard'),
    ], string='Destination', default='vendor', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Pending Approval'),
        ('approved', 'Approved'),
        ('done', 'Withdrawn'),
        ('rejected', 'Rejected'),
    ], default='draft', string='Status', tracking=True, index=True)

    line_ids = fields.One2many(
        'uellow.stock.withdrawal.line', 'withdrawal_id', string='Lines', copy=True)
    picking_id = fields.Many2one('stock.picking', string='Linked Transfer', readonly=True, copy=False)

    total_units = fields.Integer(compute='_compute_totals', string='Total Units')
    total_variants = fields.Integer(compute='_compute_totals', string='Variant Count')

    @api.depends('line_ids.qty')
    def _compute_totals(self):
        for r in self:
            r.total_variants = len(r.line_ids)
            r.total_units = sum(r.line_ids.mapped('qty'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.stock.withdrawal') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('Add at least one product before submitting.'))
            r.state = 'submitted'
            r.message_post(body=_('Withdrawal request submitted for approval.'))

    def action_approve(self):
        for r in self:
            r.state = 'approved'
            r.message_post(body=_('Withdrawal request approved.'))

    def action_reject(self):
        for r in self:
            r.state = 'rejected'
            r.message_post(body=_('Withdrawal request rejected.'))

    def action_done(self):
        """Create outgoing stock.picking from vendor sub-location."""
        self.ensure_one()
        if self.state not in ('approved',):
            raise UserError(_('Request must be approved before withdrawal.'))
        src = self.location_id
        if not src:
            raise UserError(_('No source location set for this request.'))

        if self.destination == 'scrap':
            dest = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)
        else:
            dest = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        if not dest:
            raise UserError(_('No destination location found. Check inventory settings.'))

        picking_type = self.env['stock.picking.type'].search([('code', '=', 'outgoing')], limit=1)
        moves = []
        for line in self.line_ids:
            if line.qty <= 0 or not line.product_id:
                continue
            moves.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
            }))
        if not moves:
            raise UserError(_('No valid lines to withdraw.'))

        picking = self.env['stock.picking'].create({
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id if picking_type else False,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'origin': self.name,
            'move_ids': moves,
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()
        self.picking_id = picking.id
        self.state = 'done'
        self.message_post(body=_('Stock withdrawn. Total units: %d') % self.total_units)


class StockWithdrawalLine(models.Model):
    _name = 'uellow.stock.withdrawal.line'
    _description = 'Stock Withdrawal Line'
    _order = 'withdrawal_id, id'

    withdrawal_id = fields.Many2one(
        'uellow.stock.withdrawal', string='Withdrawal', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='Product (Variant)', required=True, ondelete='restrict',
        domain=[('type', '=', 'product')])
    qty = fields.Integer('Quantity', required=True, default=1)
    available_qty = fields.Float(compute='_compute_available', string='Available in WH/VND')

    def _compute_available(self):
        for line in self:
            loc = line.withdrawal_id.location_id
            if loc and line.product_id:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', loc.id),
                ], limit=1)
                line.available_qty = quant.quantity if quant else 0.0
            else:
                line.available_qty = 0.0
