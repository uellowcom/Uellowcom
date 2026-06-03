# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uellow_vendor_carriers_enabled = fields.Boolean(
        string='Vendor Shipping Methods',
        config_parameter='uellow_delivery.vendor_carriers_enabled',
        help='Let marketplace vendors create their own delivery methods '
             '(offered at checkout only when the whole cart is theirs).')
