from odoo import fields, models


class DeliveryCarrierCompany(models.Model):
    """Surface the carrier's own kind (3rd party / in-house drivers /
    pickup) so the API can group + filter quickly."""
    _inherit = 'delivery.carrier.company'

    carrier_kind = fields.Selection([
        ('third_party',  'Third-party (Arsl, Aramex, …)'),
        ('in_house',     'In-house drivers (3-hour)'),
        ('pickup',       'Customer pickup'),
    ], default='third_party', required=True)

    description_en = fields.Char(string='Description (EN)')
    description_ar = fields.Char(string='Description (AR)')
