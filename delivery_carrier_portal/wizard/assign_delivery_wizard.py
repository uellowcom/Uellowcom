# -*- coding: utf-8 -*-
"""Assign-to-Delivery wizard (v2.1.73)
====================================
One professional dialog to dispatch sale orders to a courier company —
designed for the team that enters orders MANUALLY in Sales. Instead of
hunting through the order form's delivery tab, the user clicks
"🚚 Assign to Delivery" (form button OR list action for many orders),
picks the carrier + courier + pricing, and the wizard:
  • sets carrier company / driver / pricing rule / order type / payment type
  • auto-suggests the pricing rule from the destination governorate
  • creates the delivery.trip.line so it lands in the courier's app
  • moves delivery_status to 'assigned' (or out_for_delivery)
  • shows a live cost preview (delivery fee + cash commission)
Works on a single order or a batch selection.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


# crude city/governorate hinting so the pricing rule auto-suggests
_GOV_HINTS = {
    'capital':   ['kuwait city', 'sharq', 'mirqab', 'qibla', 'dasma', 'shuwaikh',
                  'shamiya', 'kaifan', 'qadsia', 'surra', 'مدينة الكويت', 'الكويت'],
    'hawalli':   ['hawally', 'hawalli', 'salmiya', 'salmia', 'salwa', 'jabriya',
                  'mishref', 'bayan', 'rumaithiya', 'حولي', 'السالمية'],
    'farwaniya': ['farwaniya', 'khaitan', 'khitan', 'jleeb', 'jeleeb', 'ardiya',
                  'rabiya', 'riggae', 'الفروانية'],
    'mubarak':   ['sabah al-salem', 'qurain', 'adan', 'fnaitees', 'messila',
                  'مبارك الكبير'],
    'ahmadi':    ['ahmadi', 'fahaheel', 'fahahel', 'mangaf', 'manqaf', 'mahboula',
                  'mahbola', 'fintas', 'abu halifa', 'egaila', 'wafra', 'الأحمدي'],
    'jahra':     ['jahra', 'sulaibiya', 'amghara', 'kabd', 'naeem', 'الجهراء'],
}


class AssignDeliveryWizard(models.TransientModel):
    _name = 'delivery.assign.wizard'
    _description = 'Assign Orders to Delivery'

    order_ids = fields.Many2many('sale.order', string='Orders', required=True)
    order_count = fields.Integer(compute='_compute_order_count')

    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Courier Company', required=True)
    driver_id = fields.Many2one(
        'delivery.driver', string='Courier (Driver)',
        domain="[('carrier_company_id', '=', carrier_company_id)]")
    pricing_rule_id = fields.Many2one(
        'carrier.pricing.rule', string='Pricing Rule',
        domain="[('carrier_company_id', '=', carrier_company_id)]")

    payment_method_type = fields.Selection([
        ('cash',   'Cash on Delivery'),
        ('online', 'Online (already paid)'),
        ('free',   'Free / No charge'),
    ], string='Payment', default='cash', required=True)
    carrier_order_type = fields.Selection([
        ('delivery', 'Standard Delivery'),
        ('return',   'Return'),
        ('exchange', 'Return / Exchange'),
    ], string='Order Type', default='delivery', required=True)
    set_status = fields.Selection([
        ('assigned',         'Assigned (courier will pick up)'),
        ('out_for_delivery', 'Out for delivery (already with courier)'),
    ], string='Set Status To', default='assigned', required=True)
    create_trip = fields.Boolean(
        string='Group into a Pickup Request', default=True,
        help="Add the selected orders to the carrier's OPEN pickup request "
             "(delivery.trip) — or open a new one automatically when none is "
             "open. Uncheck to dispatch without grouping.")
    note = fields.Char(string='Note to courier')

    # ── live cost preview ────────────────────────────────────────────
    preview_text = fields.Char(compute='_compute_preview')
    gov_hint = fields.Char(compute='_compute_preview')

    @api.depends('order_ids')
    def _compute_order_count(self):
        for w in self:
            w.order_count = len(w.order_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self.env.context.get('active_ids') or []
        if self.env.context.get('active_model') == 'sale.order' and ids:
            orders = self.env['sale.order'].browse(ids).filtered(
                lambda o: o.state not in ('cancel',))
            res['order_ids'] = [(6, 0, orders.ids)]
            # default payment type from the first order
            if orders and orders[0].payment_method_type:
                res['payment_method_type'] = orders[0].payment_method_type
        return res

    @api.onchange('carrier_company_id')
    def _onchange_carrier(self):
        # reset dependent fields + auto-suggest a pricing rule
        if self.driver_id and self.driver_id.carrier_company_id != self.carrier_company_id:
            self.driver_id = False
        if self.pricing_rule_id and self.pricing_rule_id.carrier_company_id != self.carrier_company_id:
            self.pricing_rule_id = False
        self._suggest_pricing_rule()

    def _detect_governorate(self):
        """Guess the governorate of the first order from its city text."""
        if not self.order_ids:
            return None
        o = self.order_ids[0]
        addr = o.partner_shipping_id or o.partner_id
        city = (getattr(o, 'delivery_address_text', '') or
                (addr.city if addr else '') or '').strip().lower()
        if not city:
            return None
        for gov, hints in _GOV_HINTS.items():
            if any(h in city for h in hints):
                return gov
        return None

    def _suggest_pricing_rule(self):
        if self.pricing_rule_id or not self.carrier_company_id:
            return
        Rule = self.env['carrier.pricing.rule']
        gov = self._detect_governorate()
        rule = False
        if gov:
            rule = Rule.search([
                ('carrier_company_id', '=', self.carrier_company_id.id),
                ('governorate', '=', gov)], limit=1)
        if not rule:
            rule = Rule.search([
                ('carrier_company_id', '=', self.carrier_company_id.id)],
                limit=1)
        if rule:
            self.pricing_rule_id = rule.id

    @api.depends('pricing_rule_id', 'payment_method_type', 'order_ids',
                 'carrier_order_type')
    def _compute_preview(self):
        for w in self:
            gov = w._detect_governorate()
            w.gov_hint = (dict(self.env['carrier.pricing.rule']
                               ._fields['governorate'].selection).get(gov, '')
                          if gov else '')
            r = w.pricing_rule_id
            if not r:
                w.preview_text = 'Select a pricing rule to preview the cost.'
                continue
            parts = ['Delivery: KD %.3f' % (r.delivery_fee or 0)]
            if w.payment_method_type == 'cash' and r.cash_commission_value:
                if r.cash_commission_type == 'percentage':
                    parts.append('Cash commission: %.1f%%' % r.cash_commission_value)
                else:
                    parts.append('Cash commission: KD %.3f' % r.cash_commission_value)
            w.preview_text = ' · '.join(parts) + (
                '   (× %d orders)' % len(w.order_ids) if len(w.order_ids) > 1 else '')

    def action_assign(self):
        self.ensure_one()
        if not self.order_ids:
            raise UserError('No orders selected.')
        trip = False
        if self.create_trip:
            # v2.2.29 — reuse the carrier's OPEN pickup request if one exists,
            # otherwise open a new one. (Was: always created a new trip.)
            trip = self.env['delivery.trip'].search([
                ('carrier_company_id', '=', self.carrier_company_id.id),
                ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ], order='date_trip desc, id desc', limit=1)
            if not trip:
                trip = self.env['delivery.trip'].create({
                    'carrier_company_id': self.carrier_company_id.id,
                    'notes': self.note or '',
                })
            elif self.note:
                trip.message_post(body='🚚 %s' % self.note)
        for order in self.order_ids:
            vals = {
                'delivery_carrier_company_id': self.carrier_company_id.id,
                'payment_method_type': self.payment_method_type,
                'carrier_order_type': self.carrier_order_type,
            }
            if self.pricing_rule_id:
                vals['pricing_rule_id'] = self.pricing_rule_id.id
            if self.driver_id:
                vals['delivery_driver_id'] = self.driver_id.id
            if trip:
                vals['delivery_trip_id'] = trip.id
            order.write(vals)
            # write() on the order already syncs a trip line when a driver
            # is set (v2.1.72). Ensure status + trip grouping.
            order.delivery_status = self.set_status
            if trip:
                line = self.env['delivery.trip.line'].search(
                    [('sale_order_id', '=', order.id)], limit=1)
                if line:
                    line.trip_id = trip.id
                elif self.driver_id:
                    self.env['delivery.trip.line'].create({
                        'trip_id': trip.id, 'sale_order_id': order.id,
                        'driver_id': self.driver_id.id})
            if self.note:
                order.message_post(body='🚚 Dispatch note: %s' % self.note)
        if trip and self.driver_id:
            trip.action_assign()
        # feedback toast
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dispatched',
                'message': '%d order(s) assigned to %s%s.' % (
                    len(self.order_ids), self.carrier_company_id.name,
                    ' · ' + self.driver_id.name if self.driver_id else ''),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
