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


def _norm_city(s):
    """v2.2.04 — Arabic-aware city normalisation for zone matching:
    unifies hamza/ta-marbuta/ya forms, drops ء, strips the definite
    article and the words محافظة/مدينة, collapses separators."""
    s = (s or '').strip().lower()
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ة', 'ه'),
                 ('ى', 'ي'), ('ئ', 'ي'), ('ؤ', 'و'), ('ء', '')):
        s = s.replace(a, b)
    for sep in ('-', '—', '–', ',', '،', '/', '·'):
        s = s.replace(sep, ' ')
    words = []
    for w in s.split():
        if w in ('محافظه', 'مدينه', 'منطقه', 'al', 'el'):
            continue
        if w.startswith('ال') and len(w) > 4:
            w = w[2:]
        if w.startswith('al-') or w.startswith('el-'):
            w = w[3:]
        if w:
            words.append(w)
    return ' '.join(words)


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
    # ── v2.1.77 — unify zones under the carrier COMPANY ──────────────
    # The courier company is the single base where all its zone rules are
    # managed. Auto-filled from the chosen method's company (kept in sync
    # by onchange + create/write below) so the One2many on the company is
    # a plain writable inverse — robust for inline editing.
    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Carrier Company', index=True,
        help='The courier company that owns this zone rule. Auto-filled '
             'from the delivery method.')
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
    # v2.2.06 — per-zone WORKING HOURS: outside this window the method
    # shows dimmed "unavailable now" for addresses in this zone. Defaults
    # 0–24 = no restriction (the carrier-level windows still apply).
    work_hour_from = fields.Float(
        'Working hours from', default=0.0,
        help='Start of this zone\'s service window, e.g. 9.0 = 09:00. '
             '0 and 24 together = no per-zone restriction.')
    work_hour_to = fields.Float(
        'Working hours to', default=24.0,
        help='End of this zone\'s service window, e.g. 21.5 = 21:30.')
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
        help='Cash-on-delivery surcharge (same currency as Price). '
             'v2.1.96 LIVE (cash-first pricing): the surcharge is included '
             'in the displayed/charged delivery price for every payment '
             'method; customers who pay ONLINE get it refunded to their '
             'wallet on capture. 0 = no surcharge.',
    )
    # v2.1.96 — per-zone refund switch: when off, online payers do NOT get
    # the surcharge back (it stays part of the delivery price).
    cod_refund_enabled = fields.Boolean(
        'Refund cash fee when paid online', default=True,
        help='When enabled, the COD surcharge included in the delivery '
             'price is credited back to the customer wallet if they pay '
             'with any non-cash method. Also gated by the global switch '
             'in Mobile App Settings.',
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

    # ── v2.1.77 — keep carrier_company_id in sync with the method ────
    @api.onchange('carrier_id')
    def _onchange_carrier_company(self):
        if self.carrier_id and self.carrier_id.carrier_company_id:
            self.carrier_company_id = self.carrier_id.carrier_company_id

    @api.model_create_multi
    def create(self, vals_list):
        Carrier = self.env['delivery.carrier']
        Company = self.env['delivery.carrier.company']
        for vals in vals_list:
            if vals.get('carrier_id') and not vals.get('carrier_company_id'):
                comp = Carrier.browse(vals['carrier_id']).carrier_company_id
                if comp:
                    vals['carrier_company_id'] = comp.id
            elif vals.get('carrier_company_id') and not vals.get('carrier_id'):
                # Created inline from the company form: attach to that
                # company's (first) delivery method.
                carrier = Carrier.search(
                    [('carrier_company_id', '=', vals['carrier_company_id'])],
                    limit=1)
                if carrier:
                    vals['carrier_id'] = carrier.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'carrier_id' in vals:
            for z in self:
                comp = z.carrier_id.carrier_company_id
                if comp and z.carrier_company_id.id != comp.id:
                    super(UellowDeliveryZone, z).write(
                        {'carrier_company_id': comp.id})
        return res

    @api.model
    def quote_for(self, carrier, partner):
        """Return the matching zone (or False) for a (carrier, partner)
        pair. City matching is case-insensitive, exact-token within the
        comma list."""
        if not carrier or not partner:
            return False
        city = (partner.city or '').strip().lower()
        # v2.2.04 — ARABIC-AWARE matching. Customers write «السالميه /
        # سالمية / الجهرا / محافظة حولي»; the configured names are
        # «السالمية / الجهراء / حولي». Normalise BOTH sides (ة=ه, أإآ=ا,
        # ى=ي, drop ء, strip ال/محافظة/مدينة) and match whole WORDS — the
        # old raw substring test even mis-routed «السالميه» to Tier 2.
        ncity = _norm_city(city)
        ncity_words = set(ncity.split())
        zones = self.sudo().search([
            ('carrier_id', '=', carrier.id),
            ('active', '=', True),
        ])
        # Two passes: explicit coverage first (governorates / cities /
        # extra tokens), then the fallback rule.
        for z in zones:
            if z._is_fallback():
                continue
            ntoks = {_norm_city(t) for t in z._match_tokens()}
            ntoks.discard('')
            hit = ncity and (
                ncity in ntoks
                or any(t in ncity_words                      # one-word token
                       or (' ' in t and t in ncity)          # multi-word token
                       for t in ntoks))
            if hit:
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


class CarrierCompanyZones(models.Model):
    """v2.1.77 — surface every zone rule of a courier company in ONE place.
    The company is the single management base for its delivery zones across
    all of its delivery methods."""
    _inherit = 'delivery.carrier.company'

    zone_rule_ids = fields.One2many(
        'uellow.delivery.zone', 'carrier_company_id',
        string='Delivery Zones',
        help='All zone-pricing rules across this company\'s delivery '
             'methods. Manage them here — the company is the base.')
    zone_rule_count = fields.Integer(
        compute='_compute_zone_rule_count', string='Zones')

    @api.depends('zone_rule_ids')
    def _compute_zone_rule_count(self):
        for c in self:
            c.zone_rule_count = len(c.zone_rule_ids)
