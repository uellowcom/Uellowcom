# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DeliveryTrip(models.Model):
    _name = 'delivery.trip'
    _description = 'Delivery Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_trip desc'

    name = fields.Char(string='Trip Reference', required=True, copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('delivery.trip'))
    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Carrier Company', required=True,
    )
    date_trip = fields.Date(string='Trip Date', required=True, default=fields.Date.today)
    state = fields.Selection([
        ('draft',       'Draft'),
        ('assigned',    'Assigned'),
        ('in_progress', 'In Progress'),
        ('done',        'Done'),
        ('cancelled',   'Cancelled'),
    ], default='draft', tracking=True)

    line_ids = fields.One2many('delivery.trip.line', 'trip_id', string='Orders')
    line_count = fields.Integer(compute='_compute_line_count', string='Orders Count')
    notes = fields.Text(string='Notes')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_assign(self):
        self.state = 'assigned'

    def action_start(self):
        self.state = 'in_progress'

    def action_done(self):
        undelivered = self.line_ids.filtered(
            lambda l: l.delivery_status not in ('delivered', 'failed', 'failed_returned')
        )
        if undelivered:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تحذير / Warning',
                    'message': '%d طلب لم يتم تسليمه بعد. هل تريد إغلاق الرحلة؟' % len(undelivered),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        self.state = 'done'

    def action_force_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'


class DeliveryTripLine(models.Model):
    _name = 'delivery.trip.line'
    _description = 'Delivery Trip Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    trip_id = fields.Many2one('delivery.trip', string='Trip', ondelete='cascade')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    driver_id = fields.Many2one('delivery.driver', string='Driver')

    delivery_status = fields.Selection(
        related='sale_order_id.delivery_status',
        string='Delivery Status',
        store=True, readonly=False,
    )

    proof_image = fields.Binary(string='Proof Image')
    proof_image_filename = fields.Char()
    proof_signature = fields.Binary(string='Signature')
    failure_reason = fields.Char(string='Failure Reason')
    failure_returned = fields.Boolean(string='Returned to Uellow', default=False)
    failure_returned_date = fields.Datetime(string='Return Date')
    notes = fields.Text(string='Driver Notes')
    delivery_date_actual = fields.Datetime(string='Actual Delivery Time')

    # Related fields
    partner_name = fields.Char(related='sale_order_id.partner_id.name', string='Customer')
    partner_phone = fields.Char(related='sale_order_id.partner_id.phone', string='Phone')
    amount_total = fields.Monetary(related='sale_order_id.amount_total', string='Amount',
                                   currency_field='currency_id')
    currency_id = fields.Many2one(related='sale_order_id.currency_id', string='Currency')
    payment_method_type = fields.Selection(related='sale_order_id.payment_method_type')
    delivery_lat = fields.Float(related='sale_order_id.delivery_lat', string='Latitude')
    delivery_lng = fields.Float(related='sale_order_id.delivery_lng', string='Longitude')
    delivery_address_text = fields.Char(related='sale_order_id.delivery_address_text')

    def action_edit(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.trip',
            'res_id': self.id,
            'view_mode': 'form',
            'flags': {'mode': 'edit'},
        }
