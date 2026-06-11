"""Uellow Brain — Phase 5: considered-purchase backend.

A `saved_for_later` flag on cart lines so a shopper can assemble an order
over days / park items they're still deciding on, without losing them or
blocking checkout. The flag is excluded from cart totals by the mobile
cart serializer (handled in cart.py). App UI ships in a later release.
"""
from odoo import fields, models


class SaleOrderLineSavedForLater(models.Model):
    _inherit = 'sale.order.line'

    brain_saved_for_later = fields.Boolean(
        'Saved for later (Brain)', default=False, copy=False,
        help='Parked by the shopper while deciding — kept in the cart but '
             'excluded from the active total until moved back.')
