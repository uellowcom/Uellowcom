from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # v2.1.51 — express services keep their price: free-shipping offers
    # (product flags, thresholds, coupons, the cart progress bar) apply
    # to STANDARD delivery only when the exclusion setting is ON.
    uellow_is_express = fields.Boolean(
        string='Express Service',
        help='Mark express/fast couriers. When "Exclude express from free '
             'shipping" is enabled in Settings, this method always keeps '
             'its full price — product flags, thresholds and free-shipping '
             'coupons do not touch it.')
