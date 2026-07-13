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

    # v2.1.75 — trip-level driver. Views referenced delivery.trip.driver_id
    # but the field never existed, which broke the form (every field went
    # read-only / the new-trip record couldn't be edited). Adding it both
    # fixes that AND is genuinely useful: set one driver for the whole
    # trip and it cascades to every order line.
    driver_id = fields.Many2one(
        'delivery.driver', string='Driver',
        domain="[('carrier_company_id', '=', carrier_company_id)]")
    line_ids = fields.One2many('delivery.trip.line', 'trip_id', string='Orders')
    line_count = fields.Integer(compute='_compute_line_count', string='Orders Count')
    notes = fields.Text(string='Notes')

    # ── PICKUP leg (Uellow warehouse → carrier sorting centre) ──────────
    # A "pickup courier" collects the whole trip from the Uellow warehouse
    # and brings it to the carrier, where the orders are received and then
    # distributed to per-region delivery drivers.
    pickup_driver_id = fields.Many2one(
        'delivery.driver', string='Pickup Courier', tracking=True,
        domain="[('carrier_company_id', '=', carrier_company_id)]",
        help='Courier who collects the orders from the Uellow warehouse and '
             'brings them to the carrier sorting centre.')
    pickup_assigned_by = fields.Selection([
        ('uellow', 'Uellow'),
        ('carrier', 'Carrier'),
    ], string='Pickup Assigned By', tracking=True)
    pickup_state = fields.Selection([
        ('unassigned', 'Awaiting pickup courier'),
        ('assigned',   'Pickup courier assigned'),
        ('collecting', 'Collecting at Uellow'),
        ('collected',  'Collected from Uellow'),
    ], compute='_compute_pickup_state', store=True, string='Pickup Stage')

    @api.depends('pickup_driver_id', 'line_ids.delivery_status')
    def _compute_pickup_state(self):
        for t in self:
            orders = t.line_ids.mapped('sale_order_id')
            pend = orders.filtered(lambda o: o.delivery_status == 'pending')
            picked = orders.filtered(lambda o: o.delivery_status == 'picked_up')
            if not t.pickup_driver_id:
                t.pickup_state = 'unassigned'
            elif not pend:
                t.pickup_state = 'collected'
            elif picked:
                t.pickup_state = 'collecting'
            else:
                t.pickup_state = 'assigned'

    def action_assign_pickup(self, driver, by='uellow'):
        """Assign a pickup courier to this trip and notify them."""
        self.ensure_one()
        self.write({'pickup_driver_id': driver.id, 'pickup_assigned_by': by})
        self.message_post(body='📦 Pickup courier <b>%s</b> assigned to collect '
                          'from the Uellow warehouse (by %s).'
                          % (driver.name, by))
        self._notify_pickup_driver(driver)
        return True

    def _notify_pickup_driver(self, driver):
        """Best-effort push to the courier's device (the trip also shows up
        in their app's Pickups list on next open)."""
        try:
            user = driver.portal_user_id
            if not user:
                return
            Push = self.env.get('mobile.customer.notification')
            if Push and hasattr(Push, 'push_event'):
                Push.sudo().push_event(
                    partner=user.partner_id,
                    event='pickup_assigned',
                    title_en='New pickup assignment 📦',
                    title_ar='مهمة استلام جديدة 📦',
                    body_en='Collect trip %s from the Uellow warehouse.' % self.name,
                    body_ar='استلم الرحلة %s من مخزن يلو.' % self.name,
                )
        except Exception:
            pass

    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        # cascade the trip driver to its order lines
        if self.driver_id:
            for ln in self.line_ids:
                ln.driver_id = self.driver_id

    def write(self, vals):
        # Notify the courier when Uellow assigns a pickup driver from the form.
        notify = ('pickup_driver_id' in vals and vals.get('pickup_driver_id'))
        res = super().write(vals)
        if vals.get('driver_id'):
            for trip in self:
                trip.line_ids.write({'driver_id': trip.driver_id.id})
        if notify:
            for trip in self:
                if not vals.get('pickup_assigned_by'):
                    trip.pickup_assigned_by = 'uellow'
                trip._notify_pickup_driver(trip.pickup_driver_id)
        return res

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
                    'title': 'Warning',
                    'message': '%d orders are not delivered yet. Close the trip anyway?' % len(undelivered),
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
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True,
                                    ondelete='cascade')
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
