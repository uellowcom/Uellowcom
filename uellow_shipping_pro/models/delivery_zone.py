from odoo import api, fields, models


class DeliveryZone(models.Model):
    """A delivery zone groups cities by distance / pricing tier.
    Examples: 'Kuwait — Capital normal', 'KW — far west remote'."""
    _name = 'delivery.zone'
    _description = 'Delivery zone (distance / pricing tier)'
    _order = 'country_id, tier, name_en'

    name_en = fields.Char(string='Name (EN)', required=True, translate=False)
    name_ar = fields.Char(string='Name (AR)', translate=False)

    country_id = fields.Many2one('res.country', string='Country', required=True,
                                 ondelete='cascade')
    governorate = fields.Selection([
        ('capital',    'Capital (العاصمة)'),
        ('hawalli',    'Hawalli (حولي)'),
        ('farwaniya',  'Farwaniya (الفروانية)'),
        ('ahmadi',     'Ahmadi (الأحمدي)'),
        ('jahra',      'Jahra (الجهراء)'),
        ('mubarak',    'Mubarak Al-Kabeer (مبارك الكبير)'),
        ('other',      'Other / non-KW'),
    ], default='other')

    # Distance tier — 0=normal, 1=remote, 2=far. Tiers drive the rate
    # surcharge per carrier so a single zone definition serves both
    # Arsl (small remote surcharge) and Uellow drivers (big remote
    # surcharge for tier 2).
    tier = fields.Selection([
        ('0', 'Normal (الأقرب)'),
        ('1', 'Remote (بعيد)'),
        ('2', 'Far  (الأبعد)'),
    ], default='0', required=True)

    city_ids = fields.One2many('delivery.city', 'zone_id', string='Cities')
    city_count = fields.Integer(compute='_compute_city_count')

    active = fields.Boolean(default=True)

    @api.depends('city_ids')
    def _compute_city_count(self):
        for z in self:
            z.city_count = len(z.city_ids)

    def name_get(self):
        out = []
        for z in self:
            tier_label = dict(self._fields['tier'].selection).get(z.tier, '')
            out.append((z.id, f"{z.name_en} · {tier_label}"))
        return out
