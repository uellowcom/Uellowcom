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

import pytz

from odoo import api, fields, models


class UellowGovernorate(models.Model):
    """v2.1.69 — governorate master data so zone rules are configured by
    PICKING areas instead of typing comma-separated tokens."""
    _name = 'uellow.governorate'
    _description = 'Governorate (delivery zones)'
    _order = 'sequence, id'

    name = fields.Char('Name (EN)', required=True)
    name_ar = fields.Char('Name (AR)')
    sequence = fields.Integer(default=10)
    country_id = fields.Many2one('res.country', string='Country')
    active = fields.Boolean(default=True)
    city_ids = fields.One2many('uellow.city', 'governorate_id',
                               string='Cities / Areas')
    city_count = fields.Integer(compute='_compute_city_count')

    def _compute_city_count(self):
        for g in self:
            g.city_count = len(g.city_ids)

    def name_get(self):
        return [(g.id, '%s — %s' % (g.name, g.name_ar)
                 if g.name_ar else g.name) for g in self]


class UellowCity(models.Model):
    """City/area master data. `aliases` holds every spelling customers
    actually type in their address (EN variants + Arabic) — matching is
    case-insensitive exact-token against name/name_ar/aliases."""
    _name = 'uellow.city'
    _description = 'City / Area (delivery zones)'
    _order = 'governorate_id, name'

    name = fields.Char('Name (EN)', required=True)
    name_ar = fields.Char('Name (AR)')
    governorate_id = fields.Many2one('uellow.governorate',
                                     string='Governorate', index=True,
                                     ondelete='set null')
    aliases = fields.Char(
        'Spelling aliases',
        help='Comma-separated extra spellings customers type, e.g. '
             '"salmia, salmiyah". Name (EN) and Name (AR) always match.')
    active = fields.Boolean(default=True)

    def all_tokens(self):
        toks = set()
        for c in self:
            for t in [c.name or '', c.name_ar or ''] + \
                     (c.aliases or '').split(','):
                t = t.strip().lower()
                if t:
                    toks.add(t)
        return toks

    def name_get(self):
        return [(c.id, '%s — %s' % (c.name, c.name_ar)
                 if c.name_ar else c.name) for c in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            args = ['|', '|', ('name', operator, name),
                    ('name_ar', operator, name),
                    ('aliases', operator, name)] + args
        return self.search(args, limit=limit).name_get()


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
    # ── v2.1.69 — professional coverage picker ───────────────────────
    # Pick whole governorates and/or individual cities with checkboxes;
    # 'all' = the fallback rule. The legacy comma-line lives on only as
    # an ADVANCED extra-tokens field.
    match_mode = fields.Selection([
        ('pick', 'Selected governorates / cities'),
        ('all', 'All cities (fallback rule)'),
    ], string='Coverage', default='pick', required=True)
    governorate_ids = fields.Many2many(
        'uellow.governorate', 'uellow_zone_gov_rel', 'zone_id', 'gov_id',
        string='Governorates',
        help='Every city/area of the checked governorates is covered.')
    city_ids = fields.Many2many(
        'uellow.city', 'uellow_zone_city_rel', 'zone_id', 'city_id',
        string='Specific cities / areas',
        help='Additional individual cities on top of the governorates.')
    coverage_summary = fields.Char(compute='_compute_coverage_summary',
                                   string='Covers')

    cities = fields.Char(
        'Extra tokens (advanced)',
        help='OPTIONAL comma-separated extra spellings not in the city '
             'master data. Legacy "*" still works as a fallback marker.',
    )

    @api.depends('match_mode', 'governorate_ids', 'city_ids', 'cities')
    def _compute_coverage_summary(self):
        for z in self:
            if z.match_mode == 'all' or '*' in (z.cities or ''):
                z.coverage_summary = '🌍 All cities (fallback)'
                continue
            parts = []
            if z.governorate_ids:
                parts.append('Gov: ' + ', '.join(
                    z.governorate_ids.mapped('name')))
            if z.city_ids:
                n = len(z.city_ids)
                names = ', '.join(z.city_ids[:4].mapped('name'))
                parts.append('Cities: %s%s' % (
                    names, ' +%d' % (n - 4) if n > 4 else ''))
            extra = [t for t in (z.cities or '').split(',') if t.strip()]
            if extra:
                parts.append('+%d token(s)' % len(extra))
            z.coverage_summary = ' · '.join(parts) or '— nothing selected —'

    def _match_tokens(self):
        """Lower-cased token set this rule covers."""
        self.ensure_one()
        toks = self.city_ids.all_tokens()
        for g in self.governorate_ids:
            toks |= g.city_ids.all_tokens()
        for t in (self.cities or '').split(','):
            t = t.strip().lower()
            if t and t != '*':
                toks.add(t)
        return toks

    def _is_fallback(self):
        self.ensure_one()
        return self.match_mode == 'all' or \
            '*' in [t.strip() for t in (self.cities or '').split(',')]
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
    # v2.1.2 — Cash-on-delivery surcharge the customer bears. Per ali@uellow:
    # when activated it is FOLDED INTO the delivery price (not shown as a
    # separate line) for COD orders only. Configured here now; the actual
    # application to the order total is intentionally NOT wired yet — it
    # stays 0 / inert until the COD-surcharge feature is switched on after
    # review. Exposed in the checkout serialization so the app can fold it in
    # the moment it's activated.
    cash_surcharge = fields.Float(
        'COD surcharge', default=0.0, digits=(10, 3),
        help='Cash-on-delivery surcharge (same currency as Price). When the '
             'COD-surcharge feature is enabled it is added INTO the delivery '
             'price for cash orders — not shown separately. 0 = no surcharge. '
             'Currently configurable only; not yet applied to order totals.',
    )
    weekday_mask = fields.Char(
        'Active weekdays (legacy)', default='1234567',
        help='Digits 1-7 (Mon-Sun). Superseded by the day checkboxes.',
    )
    # v2.1.69 — friendly per-day checkboxes (replace the digit mask).
    day_mon = fields.Boolean('Mon', default=True)
    day_tue = fields.Boolean('Tue', default=True)
    day_wed = fields.Boolean('Wed', default=True)
    day_thu = fields.Boolean('Thu', default=True)
    day_fri = fields.Boolean('Fri', default=True)
    day_sat = fields.Boolean('Sat', default=True)
    day_sun = fields.Boolean('Sun', default=True)

    _DAY_FIELDS = ['day_mon', 'day_tue', 'day_wed', 'day_thu',
                   'day_fri', 'day_sat', 'day_sun']

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
        # Two passes: explicit coverage first (governorates / cities /
        # extra tokens), then the fallback rule.
        for z in zones:
            if z._is_fallback():
                continue
            if city and city in z._match_tokens():
                if z._is_active_today():
                    return z
        for z in zones:
            if z._is_fallback() and z._is_active_today():
                return z
        return False

    def _is_active_today(self):
        """Apply weekday_mask + cutoff_time. ISO weekday is 1..7.
        v2.1.67 — LOCAL time (Asia/Kuwait default), matching the carrier
        weekly-schedule engine. The naive datetime.now() before was UTC
        (container clock): a 21:00 cutoff really fired at midnight KW."""
        self.ensure_one()
        try:
            tz = pytz.timezone(self.env.user.tz or 'Asia/Kuwait')
            now = datetime.now(tz)
        except Exception:
            now = datetime.now()
        wd = now.isoweekday()                 # 1=Mon … 7=Sun
        if not getattr(self, self._DAY_FIELDS[wd - 1], True):
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
