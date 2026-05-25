# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CarrierPricingRule(models.Model):
    _name = 'carrier.pricing.rule'
    _description = 'Carrier Pricing Rule per Zone'
    _rec_name = 'display_name'
    _order = 'carrier_company_id, zone_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('zone_name', 'governorate', 'delivery_fee')
    def _compute_display_name(self):
        for r in self:
            gov = dict(r._fields['governorate'].selection).get(r.governorate, '')
            r.display_name = f"{r.zone_name} — KD {r.delivery_fee:.3f}" if r.zone_name else ''

    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Carrier Company',
        required=True, ondelete='cascade',
    )
    zone_name = fields.Char(string='Zone Name', required=True)
    governorate = fields.Selection([
        ('capital',    'Capital (العاصمة)'),
        ('hawalli',    'Hawalli (حولي)'),
        ('farwaniya',  'Farwaniya (الفروانية)'),
        ('ahmadi',     'Ahmadi (الأحمدي)'),
        ('jahra',      'Jahra (الجهراء)'),
        ('mubarak',    'Mubarak Al-Kabeer (مبارك الكبير)'),
        ('other',      'Other'),
    ], string='Governorate')

    # ── Delivery fee ──────────────────────────────────────────────────────
    delivery_fee = fields.Float(
        string='Delivery Fee (KD)', digits=(10, 3),
        help='Standard delivery fee per order',
    )

    # ── Cash commission ───────────────────────────────────────────────────
    cash_commission_type = fields.Selection([
        ('percentage', 'Percentage %'),
        ('fixed',      'Fixed KD'),
    ], string='Cash Commission Type', default='percentage')
    cash_commission_value = fields.Float(
        string='Cash Commission Value', digits=(10, 3),
        help='If percentage: e.g. 2 = 2%. If fixed: amount in KD.',
    )

    # ── Failed / Cancellation fees ────────────────────────────────────────
    cancel_fee_full = fields.Float(
        string='Cancel Fee — Full (KD)', digits=(10, 3),
        help='Option A: delivery was attempted. Charges delivery fee + this.',
    )
    cancel_fee_only = fields.Float(
        string='Cancel Fee — Only (KD)', digits=(10, 3),
        help='Option B: cancelled before pickup. Charges this fee only.',
    )

    # ── Return / Exchange fees ────────────────────────────────────────────
    return_fee = fields.Float(
        string='Return Fee (KD)', digits=(10, 3),
        help='Carrier picks up item from customer and returns to Uellow.',
    )
    exchange_fee = fields.Float(
        string='Exchange Fee (KD)', digits=(10, 3),
        help='Carrier picks up old item AND delivers new item — 2-way trip.',
    )

    def compute_delivery_cost(self, order):
        """Compute carrier cost for a given sale.order."""
        cost = 0.0
        cancel_type = order.carrier_cancel_type or 'full'
        order_type  = order.carrier_order_type or 'delivery'

        if order_type == 'return':
            return self.return_fee
        if order_type == 'exchange':
            cost = self.exchange_fee
            if order.payment_method_type == 'cash' and order.delivery_status == 'delivered':
                cost += self._cash_commission(order.amount_total)
            return cost

        # Standard delivery
        if order.delivery_status in ('delivered', 'out_for_delivery', 'assigned'):
            cost += self.delivery_fee
            if order.payment_method_type == 'cash' and order.delivery_status == 'delivered':
                cost += self._cash_commission(order.amount_total)
        elif order.delivery_status in ('failed', 'failed_returned'):
            if cancel_type == 'full':
                cost += self.delivery_fee + self.cancel_fee_full
            else:
                cost += self.cancel_fee_only
        return cost

    def _cash_commission(self, amount):
        if self.cash_commission_type == 'percentage':
            return round(amount * self.cash_commission_value / 100, 3)
        return self.cash_commission_value
