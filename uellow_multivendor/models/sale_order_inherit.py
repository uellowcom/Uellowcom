from datetime import timedelta

from odoo import models, fields, api, _


class SaleOrder(models.Model):
    """Extend sale.order with vendor info and commission tracking."""
    _inherit = 'sale.order'

    vendor_id = fields.Many2one(
        'uellow.vendor', string='Vendor',
        index=True, ondelete='set null',
    )
    vendor_rating = fields.Float('Vendor Rating', default=0.0)
    vendor_ready_for_pickup = fields.Boolean(
        'Ready for Uellow Pickup', copy=False,
        help='Seller has prepared the order and it is ready for Uellow to collect.')
    is_quick_sale = fields.Boolean(
        'Vendor Quick Sale', copy=False, index=True,
        help='Created by a vendor via the app counter/quick-sale flow. Held in '
             'draft pending Uellow approval before fulfilment.')
    commission_id = fields.Many2one(
        'uellow.vendor.commission', string='Commission',
        readonly=True, copy=False,
    )
    flash_sale_id = fields.Many2one(
        'uellow.flash.sale', string='Flash Sale',
        ondelete='set null', copy=False,
    )
    is_flash_sale = fields.Boolean(
        compute='_compute_is_flash_sale', store=True,
    )

    @api.depends('flash_sale_id')
    def _compute_is_flash_sale(self):
        for o in self:
            o.is_flash_sale = bool(o.flash_sale_id)

    # ── Vendor fulfillment SLA ───────────────────────────────────────
    # Non-stored (depends on "now") — read live for the order hub + backend.
    vendor_fulfill_due = fields.Datetime(
        'Fulfill By', compute='_compute_vendor_sla',
        help='Deadline to confirm & ship, from the vendor SLA hours setting.')
    vendor_sla_state = fields.Selection([
        ('on_time',  'On time'),
        ('due_soon', 'Due soon'),
        ('overdue',  'Overdue'),
        ('done',     'Fulfilled'),
        ('na',       'N/A'),
    ], string='SLA', compute='_compute_vendor_sla')

    def _vendor_is_shipped(self):
        """True once every non-cancelled picking is done (or there are none)."""
        self.ensure_one()
        picks = self.picking_ids.filtered(lambda p: p.state != 'cancel')
        return bool(picks) and all(p.state == 'done' for p in picks)

    def _vendor_tracking(self):
        """A customer-style fulfilment timeline the vendor (and FBU vendors who
        have no controls) can watch. Driven by sale.order.delivery_status from
        the delivery module, falling back to order state when absent."""
        self.ensure_one()
        ds = getattr(self, 'delivery_status', False) or 'pending'
        ready = bool(self.vendor_ready_for_pickup) or ds not in ('pending', False)
        failed = ds in ('failed', 'failed_returned')
        # Map delivery_status → step index (0..3).
        if self.state == 'cancel':
            cur = -1
        elif ds == 'delivered':
            cur = 3
        elif ds in ('picked_up', 'arrived_sorting', 'assigned',
                    'accepted', 'out_for_delivery'):
            cur = 2
        elif ready:
            cur = 1
        elif self.state in ('sale', 'done'):
            cur = 0
        else:
            cur = 0
        # Driver name (best-effort; delivery module may be absent).
        driver = ''
        try:
            line = self.env['delivery.trip.line'].sudo().search(
                [('sale_order_id', '=', self.id)], limit=1)
            if line and line.trip_id and line.trip_id.driver_id:
                driver = line.trip_id.driver_id.name
        except Exception:
            pass
        steps = [
            {'key': 'confirmed', 'en': 'Confirmed',   'ar': 'تم التأكيد'},
            {'key': 'ready',     'en': 'Prepared',    'ar': 'تم التجهيز'},
            {'key': 'transit',   'en': 'In delivery', 'ar': 'قيد التوصيل'},
            {'key': 'delivered', 'en': 'Delivered',   'ar': 'تم التسليم'},
        ]
        for i, s in enumerate(steps):
            s['done'] = (cur >= i) if cur >= 0 else False
            s['current'] = (cur == i)
        return {
            'cancelled': self.state == 'cancel',
            'failed': failed,
            'current': cur,
            'driver': driver,
            'delivery_status': ds,
            'steps': steps,
        }

    @api.depends('vendor_id', 'date_order', 'state', 'picking_ids.state')
    def _compute_vendor_sla(self):
        now = fields.Datetime.now()
        for o in self:
            hours = (o.vendor_id.sla_hours or 24) if o.vendor_id else 24
            base = o.date_order or o.create_date
            if not o.vendor_id or not base or o.state == 'cancel':
                o.vendor_fulfill_due = False
                o.vendor_sla_state = 'na'
                continue
            due = base + timedelta(hours=hours)
            o.vendor_fulfill_due = due
            if o.state in ('sale', 'done') and o._vendor_is_shipped():
                o.vendor_sla_state = 'done'
            elif now > due:
                o.vendor_sla_state = 'overdue'
            elif now > (due - timedelta(hours=6)):
                o.vendor_sla_state = 'due_soon'
            else:
                o.vendor_sla_state = 'on_time'

    # ── Vendor auto-assignment ───────────────────────────────────────
    # An order's vendor_id was never being populated, so the vendor app
    # (which filters orders on vendor_id) showed nothing. Derive the
    # vendor from the order lines: the vendor with the largest line
    # subtotal "owns" the order header (single-vendor carts = the norm).
    def _uellow_vendor_from_lines(self):
        self.ensure_one()
        amounts = {}
        for line in self.order_line:
            vendor = line.product_id.product_tmpl_id.vendor_id
            if vendor:
                amounts[vendor.id] = amounts.get(vendor.id, 0.0) + (line.price_subtotal or 0.0)
        if not amounts:
            return self.env['uellow.vendor']
        best_id = max(amounts, key=lambda vid: amounts[vid])
        return self.env['uellow.vendor'].browse(best_id)

    def _uellow_assign_vendor(self):
        for order in self:
            if not order.vendor_id:
                vendor = order._uellow_vendor_from_lines()
                if vendor:
                    order.vendor_id = vendor.id

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._uellow_assign_vendor()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'order_line' in vals:
            self._uellow_assign_vendor()
        return res

    def action_confirm(self):
        self._uellow_assign_vendor()
        res = super().action_confirm()
        for order in self:
            if order.vendor_id and not order.commission_id:
                commission = self.env['uellow.vendor.commission'].create_from_order(order)
                if commission:
                    order.commission_id = commission
            # Fire the vendor's webhooks (best-effort, never blocks the sale).
            if order.vendor_id:
                self.env['vendor.webhook'].dispatch(order.vendor_id.id, 'new_order', {
                    'order_id': order.id,
                    'name': order.name,
                    'amount_total': order.amount_total,
                    'currency': order.currency_id.name,
                    'date': order.date_order,
                    'state': order.state,
                })
        return res
