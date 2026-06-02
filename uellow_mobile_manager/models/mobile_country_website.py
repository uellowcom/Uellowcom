# -*- coding: utf-8 -*-
"""
mobile.country.website — Map a country (or list of countries) to the
website that the mobile app should connect to. Each app build is
country-aware: launch sequence asks the user their country, defaults
from geo-IP, and picks the matching website.

How content editors use it:
  Mobile App Manager → Country Routing → New mapping
     Country:      Kuwait
     Website:      Kuwait Mobile App
     Currency:     KWD                  (informational; website already has its own)
     Language:     ar_001 (default)
     Active:       True

The app calls /api/mobile/v2/app/geo at startup → server replies with
the recommended website given the request's IP. If the user later
travels to a different country, the next /geo call detects the
mismatch and the app prompts "Stay or Switch?". If the user has set
a manual override (stored in their mobile.session), the prompt is
suppressed — their choice sticks.
"""
from odoo import api, fields, models


class MobileCountryWebsite(models.Model):
    _name = 'mobile.country.website'
    _description = 'Country → Mobile-app Website Mapping'
    _order = 'sequence, country_id'
    _rec_name = 'country_id'

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    country_id = fields.Many2one(
        'res.country', string='Country', required=True, ondelete='cascade',
    )
    website_id = fields.Many2one(
        'website', string='Mobile-app Website', required=True,
        ondelete='cascade',
        help='Which Odoo website the Flutter app should connect to when '
             'the user is in this country.',
    )
    default_language = fields.Many2one(
        'res.lang', string='Default Language',
        help='Pre-select this language in the country picker. The user '
             'can still change it. If empty, app uses the phone locale.',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Display Currency',
        help='Informational — used by the country picker. The website\'s '
             'own currency is what the cart actually uses.',
    )
    phone_code = fields.Integer(
        related='country_id.phone_code', string='Phone Code', readonly=True,
    )
    flag_emoji = fields.Char(
        string='Flag Emoji', size=4,
        help='e.g. 🇰🇼 — shown in the country picker. Auto-derived from '
             'country code if left blank.',
    )

    is_primary = fields.Boolean(
        string='Primary',
        help='Marks the "fallback" country when geo-IP fails. Only one '
             'per app should be primary.',
    )

    _sql_constraints = [
        ('uniq_country', 'unique(country_id)',
         'Each country can only map to one mobile website.'),
    ]

    @api.model
    def find_for_country_code(self, code):
        """Return the mapping for an ISO country code, or the primary
        fallback, or False. Used by the geo endpoint."""
        if code:
            m = self.search([
                ('country_id.code', '=', (code or '').upper()),
                ('active', '=', True),
            ], limit=1)
            if m:
                return m
        return self.search([('is_primary', '=', True), ('active', '=', True)], limit=1)

    @api.model
    def find_for_ip(self, ip_address):
        """Resolve an IP to country using Odoo's built-in GeoIP."""
        try:
            country_code = self.env['res.country']._get_country_from_ip(ip_address)
        except Exception:
            country_code = None
        # Newer Odoo helper returns a record; older returns a code.
        if hasattr(country_code, 'code'):
            country_code = country_code.code
        return self.find_for_country_code(country_code)

    def to_dict(self):
        self.ensure_one()
        from ..controllers.api_v2._common import bilingual
        return {
            'country': {
                'id': self.country_id.id,
                'code': self.country_id.code,
                'name': bilingual(self.country_id, 'name'),
                'phone_code': self.phone_code or '',
                'flag': self.flag_emoji or _flag_from_code(self.country_id.code),
            },
            'website': {
                'id': self.website_id.id,
                'name': self.website_id.name,
                'domain': self.website_id.domain or '',
                'api_base': self._api_base(),
            },
            'default_language': self.default_language.code if self.default_language else None,
            'currency': self.currency_id.name if self.currency_id else self.website_id.currency_id.name,
            'currency_symbol': self.currency_id.symbol if self.currency_id else self.website_id.currency_id.symbol,
        }

    def _api_base(self):
        """Strip protocol/path, return https://<domain> for the app to
        switch its base URL to."""
        d = (self.website_id.domain or '').strip().rstrip('/')
        if not d:
            return ''
        if d.startswith('http'):
            return d
        return f'https://{d}'


def _flag_from_code(code):
    """Convert an ISO 3166-1 alpha-2 code to its regional-indicator
    flag emoji. Pure-python so no extra dependency."""
    if not code or len(code) != 2:
        return ''
    return ''.join(chr(0x1F1E6 + (ord(c) - ord('A'))) for c in code.upper())
