# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Delivery Carrier', tracking=True,
    )
    delivery_trip_id = fields.Many2one('delivery.trip', string='Delivery Trip')
    delivery_driver_id = fields.Many2one('delivery.driver', string='Assigned Driver')

    delivery_status = fields.Selection(
        selection=[
            ('pending',          'Pending'),
            # NEW — collected from the Uellow warehouse by the carrier's
            # pickup courier and in transit to the carrier sorting centre.
            ('picked_up',        'Picked Up (in transit to carrier)'),
            ('arrived_sorting',  'Arrived at Sorting Center'),
            ('assigned',         'Assigned to Driver'),
            # v2.2.33 — driver ACCEPTED the assignment (order is with the
            # courier) but has NOT pressed "Start delivery" yet, so no live
            # tracking. 'out_for_delivery' = courier is actually on the way.
            ('accepted',         'Accepted by Driver'),
            ('out_for_delivery', 'Out for Delivery'),
            ('delivered',        'Delivered'),
            ('failed',           'Failed'),
            ('failed_returned',  'Failed & Returned'),
        ],
        string='Delivery Status',
        default='pending',
        tracking=True,
    )

    # Return system
    # ── Pay Link fields ──────────────────────────────────────
    pay_link_status = fields.Selection([
        ('none',    'Not Sent'),
        ('sent',    'Link Sent'),
        ('paid',    'Paid via Link'),
        ('failed',  'Payment Failed'),
    ], string='Pay Link Status', default='none', tracking=True)
    pay_link_url        = fields.Char(string='Payment Link URL')
    pay_link_ref        = fields.Char(string='Payment Reference')
    pay_link_amount     = fields.Float(string='Paid Amount', digits=(10,3))
    pay_link_date       = fields.Datetime(string='Payment Date')
    pay_link_provider   = fields.Char(string='Payment Provider')
    pay_link_sent_by    = fields.Many2one('res.users', string='Link Sent By')
    pay_link_sent_date  = fields.Datetime(string='Link Sent Date')

    return_status = fields.Selection([
        ('none',              'N/A'),
        ('awaiting_return',   'Awaiting Return'),
        ('return_scheduled',  'Return Scheduled'),
        ('return_in_transit', 'In Transit to Uellow'),
        ('returned_received', 'Received by Uellow'),
    ], string='Return Status', default='none', tracking=True)

    return_scheduled_date = fields.Datetime(string='Scheduled Return Date')
    return_received_date  = fields.Datetime(string='Received Date')
    return_received_by    = fields.Char(string='Received By (Employee)')
    return_signature      = fields.Binary(string='Return Signature')
    return_notes          = fields.Text(string='Return Notes')
    return_checklist_ok   = fields.Boolean(string='Product OK on Return')

    payment_method_type = fields.Selection([
        ('cash',   'Cash on Delivery'),
        ('online', 'Online Payment'),
        ('free',   'Free / No Charge'),
    ], string='Payment Method Type', default='online')

    cash_collection_status = fields.Selection([
        ('not_applicable', 'Not Applicable'),
        ('pending',        'Pending Collection'),
        ('collected',      'Collected'),
        ('remitted',       'Remitted to Uellow'),
    ], string='Cash Status', default='not_applicable', tracking=True)

    cash_remittance_id = fields.Many2one(
        'delivery.cash.remittance', string='Cash Remittance')
    delivery_lat = fields.Float(string='Delivery Latitude', digits=(10, 7))
    delivery_lng = fields.Float(string='Delivery Longitude', digits=(10, 7))
    delivery_address_text = fields.Char(string='Delivery Address (Map)')
    delivery_date_actual = fields.Datetime(string='Actual Delivery Time')
    # ── Carrier pricing fields ───────────────────────────────────────────
    pricing_rule_id = fields.Many2one(
        'carrier.pricing.rule', string='Pricing Rule',
        domain="[('carrier_company_id', '=', delivery_carrier_company_id)]",
    )
    carrier_order_type = fields.Selection([
        ('delivery',  'Standard Delivery'),
        ('return',    'Return'),
        ('exchange',  'Return / Exchange'),
    ], string='Order Type', default='delivery')
    carrier_cancel_type = fields.Selection([
        ('full', 'Option A — Delivery + Cancel fee'),
        ('only', 'Option B — Cancel fee only'),
    ], string='Cancellation Billing', default='full')

    carrier_delivery_fee     = fields.Float(string='Delivery Fee (KD)',     digits=(10,3), compute='_compute_carrier_cost', store=True)
    carrier_cash_commission  = fields.Float(string='Cash Commission (KD)',  digits=(10,3), compute='_compute_carrier_cost', store=True)
    carrier_cancel_fee       = fields.Float(string='Cancellation Fee (KD)', digits=(10,3), compute='_compute_carrier_cost', store=True)
    carrier_return_fee       = fields.Float(string='Return/Exchange Fee (KD)', digits=(10,3), compute='_compute_carrier_cost', store=True)
    carrier_net_cost         = fields.Float(string='Net Carrier Cost (KD)', digits=(10,3), compute='_compute_carrier_cost', store=True)

    @api.depends('pricing_rule_id', 'delivery_status', 'payment_method_type',
                 'amount_total', 'carrier_order_type', 'carrier_cancel_type')
    def _compute_carrier_cost(self):
        for order in self:
            r = order.pricing_rule_id
            if not r:
                order.carrier_delivery_fee = order.carrier_cash_commission = 0
                order.carrier_cancel_fee   = order.carrier_return_fee = order.carrier_net_cost = 0
                continue

            otype  = order.carrier_order_type or 'delivery'
            ctype  = order.carrier_cancel_type or 'full'
            status = order.delivery_status
            is_cash = order.payment_method_type == 'cash'

            dfee = ccmm = cfee = rfee = 0.0

            if otype == 'return':
                rfee = r.return_fee

            elif otype == 'exchange':
                rfee = r.exchange_fee
                if is_cash and status == 'delivered':
                    ccmm = r._cash_commission(order.amount_total)

            else:
                # Standard delivery — show delivery fee as soon as rule is set
                if status in ('failed', 'failed_returned'):
                    if ctype == 'full':
                        dfee = r.delivery_fee
                        cfee = r.cancel_fee_full
                    else:
                        cfee = r.cancel_fee_only
                else:
                    # pending / assigned / out_for_delivery / delivered — always show delivery fee
                    dfee = r.delivery_fee
                    if is_cash and status == 'delivered':
                        ccmm = r._cash_commission(order.amount_total)

            order.carrier_delivery_fee    = dfee
            order.carrier_cash_commission = ccmm
            order.carrier_cancel_fee      = cfee
            order.carrier_return_fee      = rfee
            order.carrier_net_cost        = dfee + ccmm + cfee + rfee

    @api.onchange('pricing_rule_id', 'carrier_order_type', 'carrier_cancel_type', 'payment_method_type')
    def _onchange_pricing(self):
        """Trigger recompute immediately in the UI when pricing fields change."""
        self._compute_carrier_cost()

    carrier_portal_remittance_id = fields.Many2one(
        'delivery.cash.remittance',
        string='Portal Remittance',
        ondelete='set null',
    )
    carrier_order_ref = fields.Char(
        string='Carrier Order Ref',
        help='Reference number assigned by the carrier company for this specific order',
        tracking=True,
    )


    def write(self, vals):
        res = super().write(vals)
        # v2.1.72 — assigning a driver on the order form must make the
        # order appear in the DRIVER APP. The app reads delivery.trip.line
        # (by driver_id); a bare delivery_driver_id never created one, so
        # directly-assigned orders were invisible to the driver. Sync a
        # trip line on assignment + flip status to 'assigned'.
        if 'delivery_driver_id' in vals and vals.get('delivery_driver_id'):
            for order in self:
                order._sync_driver_trip_line()
        return res

    def _sync_driver_trip_line(self):
        self.ensure_one()
        drv = self.delivery_driver_id
        if not drv:
            return
        # v2.2.32 — every assigned order must belong to a TRIP so it shows in
        # the driver app's Trips tab too (not just the orders list). Reuse the
        # order's trip, else the driver/carrier's OPEN trip, else open a new
        # one. (Directly-assigned orders used to get a trip-less line, so the
        # Trips tab + trip-based stats stayed empty.)
        Trip = self.env['delivery.trip'].sudo()
        trip = self.delivery_trip_id
        carrier = self.delivery_carrier_company_id or drv.carrier_company_id
        if not trip and carrier:
            trip = Trip.search([
                ('carrier_company_id', '=', carrier.id),
                ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ], order='date_trip desc, id desc', limit=1)
            if not trip:
                trip = Trip.create({
                    'carrier_company_id': carrier.id,
                    'driver_id': drv.id,
                })
            self.delivery_trip_id = trip.id
        Line = self.env['delivery.trip.line'].sudo()
        line = Line.search([('sale_order_id', '=', self.id)], limit=1)
        if line:
            vals = {}
            if line.driver_id.id != drv.id:
                vals['driver_id'] = drv.id
            if trip and line.trip_id.id != trip.id:
                vals['trip_id'] = trip.id
            if vals:
                line.write(vals)
        else:
            Line.create({
                'sale_order_id': self.id,
                'driver_id': drv.id,
                'trip_id': trip.id if trip else False,
            })
        # Move to 'assigned' so the driver sees it as a new active task
        # (don't downgrade an already-progressed status).
        if self.delivery_status in ('pending', 'arrived_sorting', False):
            self.delivery_status = 'assigned'

    # ── v2.2.33 — auto pickup-request on order confirmation ──────────────
    def _resolve_carrier_company(self):
        """Best-effort carrier for an order at confirmation time:
        explicit carrier on the order → company flagged is_default → first
        active company. Returns a delivery.carrier.company or empty rs."""
        self.ensure_one()
        if self.delivery_carrier_company_id:
            return self.delivery_carrier_company_id
        Cc = self.env['delivery.carrier.company'].sudo()
        default = Cc.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        return default or Cc.search([('active', '=', True)], limit=1)

    def _ensure_pickup_request(self):
        """Attach this order to its carrier's OPEN pickup request (delivery.trip),
        creating one if none is open. The line is created WITHOUT a driver and
        the order stays 'pending' until the carrier RECEIVES it at the sorting
        center. Idempotent — safe to call again."""
        self.ensure_one()
        if self.state != 'sale' or self.delivery_status in (
                'delivered', 'failed', 'failed_returned'):
            return
        carrier = self._resolve_carrier_company()
        if not carrier:
            return
        if not self.delivery_carrier_company_id:
            self.delivery_carrier_company_id = carrier.id
        Trip = self.env['delivery.trip'].sudo()
        trip = self.delivery_trip_id
        if not trip:
            trip = Trip.search([
                ('carrier_company_id', '=', carrier.id),
                ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ], order='date_trip desc, id desc', limit=1)
            if not trip:
                trip = Trip.create({'carrier_company_id': carrier.id})
            self.delivery_trip_id = trip.id
        Line = self.env['delivery.trip.line'].sudo()
        line = Line.search([('sale_order_id', '=', self.id)], limit=1)
        if not line:
            Line.create({'sale_order_id': self.id, 'trip_id': trip.id})
        elif not line.trip_id:
            line.trip_id = trip.id

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            try:
                order._ensure_pickup_request()
            except Exception:
                # never block a sale confirmation on the dispatch side-write
                pass
        return res

    def action_confirm_return_received(self):
        """Opens wizard-like dialog via return URL - handled via portal controller."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Confirm Return Receipt',
            'res_model': 'sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
