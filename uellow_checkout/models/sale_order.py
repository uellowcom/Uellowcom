# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import ValidationError


class UellowSaleOrder(models.Model):
    _inherit = 'sale.order'

    # Delivery coordinates fields
    delivery_latitude  = fields.Float(string='Delivery Latitude',  digits=(10, 8))
    delivery_longitude = fields.Float(string='Delivery Longitude', digits=(11, 8))
    delivery_map_url   = fields.Char(string='Map Link', compute='_compute_map_url', store=False)
    delivery_address_detail = fields.Text(string='Delivery Address Detail')

    def _compute_map_url(self):
        for rec in self:
            if rec.delivery_latitude and rec.delivery_longitude:
                rec.delivery_map_url = (
                    'https://www.google.com/maps?q=%s,%s' %
                    (rec.delivery_latitude, rec.delivery_longitude)
                )
            else:
                rec.delivery_map_url = False

    def _check_cart_is_ready_to_be_paid(self):
        """Override: skip carrier_id check — we handle shipping separately."""
        if not self._is_cart_ready():
            raise ValidationError(
                "Your cart is not ready to be paid, please verify previous steps."
            )
        return True
