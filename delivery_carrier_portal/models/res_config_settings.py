# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uellow_vendor_carriers_enabled = fields.Boolean(
        string='Vendor Shipping Methods',
        config_parameter='uellow_delivery.vendor_carriers_enabled',
        help='Let marketplace vendors create their own delivery methods '
             '(offered at checkout only when the whole cart is theirs).')

    uellow_inventory_confirm_btn = fields.Boolean(
        string='Inventory "Confirm Delivery" Button',
        config_parameter='uellow_delivery.inventory_confirm_btn',
        default=True,
        help='Show a "Confirm Delivery / تأكيد التوصيل" button on outgoing '
             'delivery orders so warehouse staff can mark the sale order as '
             'delivered (and notify the customer) straight from Inventory.')

    uellow_inventory_settle_btn = fields.Boolean(
        string='Inventory "Deliver + Settle" Button',
        config_parameter='uellow_delivery.inventory_settle_btn',
        default=True,
        help='Show a one-click button on outgoing delivery orders that confirms '
             'delivery, creates & posts the invoice, marks it PAID (settled via a '
             'reconciled bank entry) and locks the order.')
