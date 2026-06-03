from odoo import api, fields, models


class CarrierPricingRule(models.Model):
    """Extends the existing carrier.pricing.rule with:
    - zone_id link (uses the new delivery.zone records instead of free-
      text zone_name) so a single rule applies to many cities.
    - cash_surcharge_fixed: separate from the percentage commission so
      Arsl's "+0.25 KD if paid cash" is expressible.
    - time_window_*: hours of day (0–24) when this carrier is selectable;
      Uellow drivers (3-hour delivery) only appear between 14:00 and 21:00.
    """
    _inherit = 'carrier.pricing.rule'

    zone_id = fields.Many2one(
        'delivery.zone', string='Delivery zone',
        ondelete='set null',
        help='Pick a zone defined under Shipping → Zones. The zone tier '
             '(normal/remote/far) drives which surcharge tier this rule '
             'should be priced at.',
    )

    cash_surcharge_fixed = fields.Float(
        string='Cash surcharge — fixed (KD)', digits=(10, 3),
        help='Flat extra charged when the customer chooses Cash on '
             'Delivery (Arsl example: +0.25 KD on every COD order).',
    )

    time_window_start = fields.Float(
        string='Available from (hour)',
        help='0-23.99 (24h clock). When start = end, the carrier is '
             'always available.',
    )
    time_window_end = fields.Float(
        string='Available until (hour)',
        help='0-23.99 (24h clock). End is exclusive.',
    )

    def _within_time_window(self, dt):
        """True if `dt` (datetime, server tz) lands inside the rule's
        availability window. Window 0-0 ⇒ always."""
        self.ensure_one()
        if self.time_window_start == self.time_window_end:
            return True
        hr = dt.hour + dt.minute / 60.0
        return self.time_window_start <= hr < self.time_window_end

    @api.depends('zone_name', 'zone_id', 'governorate', 'delivery_fee')
    def _compute_display_name(self):
        for r in self:
            label = r.zone_id.name_en if r.zone_id else (r.zone_name or '')
            r.display_name = f"{label} — KD {r.delivery_fee:.3f}" if label else ''
