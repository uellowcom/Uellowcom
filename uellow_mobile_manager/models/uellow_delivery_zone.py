# -*- coding: utf-8 -*-
"""
Uellow Delivery Zone
====================
Maps a `delivery.carrier` to a list of zone-rule rows. Each rule pairs
a comma-separated list of city tokens (lower-cased) with a fixed price
plus an optional cutoff time (for express / same-day carriers).

Example setup:
  Carrier "Next-day delivery":
    rule A — cities: *           → 1.250 KD
    rule B — cities: abdali, sabah al ahmad → 2.500 KD

  Carrier "3-hour express":
    rule A — cities: *           → 2.000 KD, cutoff 21:00
    rule B — cities: jahra, mahboula, fahaheel → 2.500 KD, cutoff 21:00

The `delivery.carrier` is overridden so its rate_shipment() consults this
table first, then falls back to whatever fixed price the carrier had.
"""
from datetime import datetime, time

from odoo import api, fields, models


class UellowDeliveryZone(models.Model):
    _name = 'uellow.delivery.zone'
    _description = 'Uellow Delivery Zone Rule'
    _order = 'sequence, id'

    name = fields.Char('Zone Name', required=True,
                       help='Display label, e.g. "Standard cities" or "Remote KW".')
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    carrier_id = fields.Many2one(
        'delivery.carrier', string='Delivery Carrier',
        required=True, ondelete='cascade', index=True,
    )
    cities = fields.Char(
        'Cities', required=True,
        help='Comma-separated city tokens (lower-cased). Use "*" to '
             'match all cities — typically your fallback / default rule.',
    )
    price = fields.Float(
        'Price', required=True, digits=(10, 3),
        help='Flat delivery price for any address in this zone.',
    )
    cutoff_time = fields.Char(
        'Cutoff time', default='',
        help='HH:MM (24h). Orders placed after this time the same day are '
             'pushed to the next eligible day. Leave blank for no cutoff.',
    )
    # v2.0.97 — purely informational delivery-window label shown to the
    # customer in checkout (no pricing/logic impact). Bilingual per the
    # EN-primary + AR rule; AR falls back to EN when left blank.
    delivery_window = fields.Char(
        'Delivery window (EN)', default='',
        help='Free-text window/ETA shown in checkout, e.g. '
             '"2:00 PM – 9:00 PM" or "Same day". Display only.',
    )
    delivery_window_ar = fields.Char(
        'Delivery window (AR)', default='',
        help='Arabic override for the delivery window. Leave blank to reuse '
             'the English label.',
    )
    weekday_mask = fields.Char(
        'Active weekdays', default='1234567',
        help='Digits 1-7 (Mon-Sun) indicating which days this rule is active. '
             'Example: "12345" = Mon-Fri only.',
    )

    @api.model
    def quote_for(self, carrier, partner):
        """Return the matching zone (or False) for a (carrier, partner)
        pair. City matching is case-insensitive, exact-token within the
        comma list."""
        if not carrier or not partner:
            return False
        city = (partner.city or '').strip().lower()
        zones = self.sudo().search([
            ('carrier_id', '=', carrier.id),
            ('active', '=', True),
        ])
        # Two passes: exact city tokens first, then wildcard fallback
        for z in zones:
            tokens = [t.strip().lower() for t in (z.cities or '').split(',') if t.strip()]
            if city and city in tokens:
                if z._is_active_today():
                    return z
        for z in zones:
            tokens = [t.strip().lower() for t in (z.cities or '').split(',')]
            if '*' in tokens:
                if z._is_active_today():
                    return z
        return False

    def _is_active_today(self):
        """Apply weekday_mask + cutoff_time. ISO weekday is 1..7."""
        self.ensure_one()
        now = datetime.now()
        wd = str(now.isoweekday())
        if self.weekday_mask and wd not in self.weekday_mask:
            return False
        if self.cutoff_time and ':' in self.cutoff_time:
            try:
                hh, mm = [int(x) for x in self.cutoff_time.split(':')[:2]]
                if now.time() > time(hh, mm):
                    return False
            except Exception:
                pass
        return True


class DeliveryCarrierZoneHook(models.Model):
    _inherit = 'delivery.carrier'

    uellow_zone_ids = fields.One2many(
        'uellow.delivery.zone', 'carrier_id', string='Uellow Zone Rules',
    )

    def uellow_rate(self, order):
        """Return (price, currency) using the matching zone rule for
        this order's partner. Falls back to the carrier's fixed_price."""
        self.ensure_one()
        zone = self.env['uellow.delivery.zone'].sudo().quote_for(
            self, order.partner_shipping_id or order.partner_id,
        )
        if zone:
            return zone.price, self.product_id.currency_id or order.currency_id
        return getattr(self, 'fixed_price', 0.0), order.currency_id
