from odoo import api, fields, models


class DeliveryCity(models.Model):
    """A city / district that maps to a delivery zone. Bilingual names
    are matched against the address picker (which uses Nominatim) so
    the spelling lines up with Google Maps / OSM."""
    _name = 'delivery.city'
    _description = 'City / district mapped to a delivery zone'
    _order = 'country_id, zone_id, name_en'

    name_en = fields.Char(string='Name (EN)', required=True)
    name_ar = fields.Char(string='Name (AR)')

    country_id = fields.Many2one('res.country', string='Country', required=True,
                                 ondelete='cascade')
    zone_id = fields.Many2one('delivery.zone', string='Delivery zone',
                              ondelete='set null')

    # Optional geo for reverse-matching from a tap on the map
    lat = fields.Float(string='Latitude', digits=(10, 6))
    lng = fields.Float(string='Longitude', digits=(10, 6))

    aliases = fields.Char(
        string='Aliases (comma-separated)',
        help='Alternative spellings the address picker may return — '
             'lower-case, accent-stripped. Lookups are tolerant.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('city_name_country_uniq',
         'unique(country_id, name_en)',
         'A city with the same EN name already exists in this country.'),
    ]

    def name_get(self):
        return [(c.id, f"{c.name_en}{f' ({c.name_ar})' if c.name_ar else ''}")
                for c in self]

    @api.model
    def lookup(self, country_code, raw_name):
        """Best-effort match: tries EN, AR, aliases, and case/spaces."""
        if not raw_name:
            return self.browse()
        Country = self.env['res.country'].sudo()
        country = Country.search([('code', '=', country_code.upper())], limit=1)
        if not country:
            return self.browse()
        norm = lambda s: ''.join(c for c in (s or '').lower()
                                 if c.isalnum())
        target = norm(raw_name)
        for c in self.sudo().search([('country_id', '=', country.id),
                                     ('active', '=', True)]):
            if norm(c.name_en) == target or norm(c.name_ar) == target:
                return c
            if c.aliases:
                for a in c.aliases.split(','):
                    if norm(a) == target:
                        return c
        return self.browse()
