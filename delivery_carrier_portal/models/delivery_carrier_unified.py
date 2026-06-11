# -*- coding: utf-8 -*-
"""
Unified delivery architecture
=============================
`delivery.carrier` (Odoo native) is THE single spine for every shipping
method. This extension wires the three previously-parallel systems into
one record:

  1. Odoo's own delivery.carrier        → pricing, checkout, set_delivery_line
  2. delivery.carrier.company (portal)  → which courier company executes it
  3. uellow.delivery.zone / delivery.city (shipping pro) → per-zone pricing

…and adds the operational scoping the marketplace needs:

  • carrier_company_id  — the courier that fulfils this method
  • website_ids         — which country-websites offer it (empty = all)
  • country_ids         — destination countries (empty = all)
  • channel             — app / website / both
  • date_from/date_to   — seasonal methods (e.g. Ramadan express)
  • availability_ids    — weekday + hour windows (e.g. Fri 14:00–21:00)
  • vendor_id           — vendor-owned method (gated by a global setting)

Checkout calls `available_for(website, country_code, channel)` so only
methods valid RIGHT NOW for THIS website/country/channel are offered.
"""
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

WEEKDAYS = [
    ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
    ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
]


class DeliveryCarrierAvailability(models.Model):
    _name = 'delivery.carrier.availability'
    _description = 'Delivery Method Availability Window'
    _order = 'weekday, hour_from'

    carrier_id = fields.Many2one('delivery.carrier', required=True,
                                 ondelete='cascade', index=True)
    weekday = fields.Selection(WEEKDAYS, required=True)
    hour_from = fields.Float('From (hour)', default=0.0,
                             help='24h clock, e.g. 14.5 = 2:30 PM')
    hour_to = fields.Float('To (hour)', default=24.0)

    _sql_constraints = [
        ('hours_sane', 'CHECK(hour_from >= 0 AND hour_to <= 24 '
                       'AND hour_from < hour_to)',
         'Hours must be within 0–24 and From < To.'),
    ]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # ── Who executes it ────────────────────────────────────────────────
    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Courier Company',
        help='The delivery company (portal record) that fulfils orders '
             'shipped with this method. Links drivers, trips, remittance.')

    # ── Where / when / which channel ───────────────────────────────────
    uellow_website_ids = fields.Many2many(
        'website', 'delivery_carrier_website_rel', 'carrier_id', 'website_id',
        string='Websites', help='Country-websites that offer this method. '
                                'Empty = every website.')
    uellow_country_ids = fields.Many2many(
        'res.country', 'delivery_carrier_country_rel', 'carrier_id',
        'country_id', string='Destination Countries',
        help='Empty = deliver everywhere the website ships.')
    uellow_channel = fields.Selection([
        ('both', 'App + Website'),
        ('app', 'Mobile App only'),
        ('website', 'Website only'),
    ], string='Sales Channel', default='both', required=True)
    uellow_date_from = fields.Date('Available From',
                                   help='Seasonal start (empty = always).')
    uellow_date_to = fields.Date('Available Until')
    availability_ids = fields.One2many(
        'delivery.carrier.availability', 'carrier_id',
        string='Weekly Schedule',
        help='Empty = available 24/7. Otherwise the method only shows '
             'during these windows (website timezone).')

    # ── Public label + description (website / app) ─────────────────────
    public_label_en = fields.Char(
        'Public Name (EN)',
        help='Customer-facing name shown in the app/website checkout. '
             'Empty = use the internal method name.')
    public_label_ar = fields.Char('Public Name (AR)')
    public_desc_en = fields.Char(
        'Public Description (EN)',
        help='Small line shown under the method name in checkout, e.g. '
             '"Delivered within 2–4 hours inside Kuwait City".')
    public_desc_ar = fields.Char('Public Description (AR)')

    # ── Vendor-owned methods ───────────────────────────────────────────
    vendor_id = fields.Many2one(
        'uellow.vendor', string='Owned by Vendor', index=True,
        help='When set, this is a vendor\'s own delivery method (only '
             'offered on that vendor\'s products, and only if vendor '
             'carriers are enabled in Settings).')

    availability_summary = fields.Char(
        compute='_compute_availability_summary', string='Schedule')

    @api.depends('availability_ids', 'uellow_date_from', 'uellow_date_to')
    def _compute_availability_summary(self):
        names = dict(WEEKDAYS)
        for c in self:
            if not c.availability_ids:
                c.availability_summary = '24/7'
                continue
            parts = []
            for a in c.availability_ids.sorted('weekday'):
                parts.append('%s %02d:%02d–%02d:%02d' % (
                    names[a.weekday][:3],
                    int(a.hour_from), round((a.hour_from % 1) * 60),
                    int(a.hour_to), round((a.hour_to % 1) * 60)))
            c.availability_summary = ', '.join(parts)

    # ── Availability engine ────────────────────────────────────────────
    def _now_local(self):
        tz = pytz.timezone(self.env.user.tz or 'Asia/Kuwait')
        return datetime.now(tz)

    def is_available_now(self):
        """Date range + weekly schedule check (website timezone)."""
        self.ensure_one()
        now = self._now_local()
        today = now.date()
        if self.uellow_date_from and today < self.uellow_date_from:
            return False
        if self.uellow_date_to and today > self.uellow_date_to:
            return False
        if not self.availability_ids:
            return True
        wd = str(now.weekday())          # Monday = 0 … Sunday = 6
        hour = now.hour + now.minute / 60.0
        return any(a.weekday == wd and a.hour_from <= hour < a.hour_to
                   for a in self.availability_ids)

    def available_for(self, website=None, country_code=None, channel='app',
                      check_time=True):
        """Full eligibility check used by checkout / the mobile API.
        v2.1.98 — `check_time=False` skips the time-of-day window so the
        picker can SHOW an after-hours method dimmed ("unavailable now")
        instead of hiding it entirely."""
        self.ensure_one()
        if self.uellow_channel not in ('both', channel):
            return False
        if website and self.uellow_website_ids and \
                website.id not in self.uellow_website_ids.ids:
            return False
        if country_code and self.uellow_country_ids and \
                country_code.upper() not in \
                [c.code for c in self.uellow_country_ids]:
            return False
        if self.vendor_id:
            enabled = self.env['ir.config_parameter'].sudo().get_param(
                'uellow_delivery.vendor_carriers_enabled', '')
            if enabled not in ('1', 'True', 'true'):
                return False
        return self.is_available_now() if check_time else True

    def available_for_order(self, order, website=None, country_code=None,
                            channel='app', check_time=True):
        # available_for + the vendor-cart rule: a vendor-owned method is
        # only offered when EVERY product in the cart belongs to that
        # vendor (mixed carts can't be delivered by one vendor).
        self.ensure_one()
        if not self.available_for(website=website, country_code=country_code,
                                  channel=channel, check_time=check_time):
            return False
        if self.vendor_id and order:
            lines = order.order_line.filtered(
                lambda l: not l.display_type and not l.is_reward_line
                and not getattr(l, 'is_delivery', False))
            if not lines:
                return False
            for l in lines:
                v = getattr(l.product_id.product_tmpl_id, 'vendor_id', False)
                if not v or v.id != self.vendor_id.id:
                    return False
        return True
