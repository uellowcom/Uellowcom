"""Beena Order: extension of sale.order to mark orders/quotations placed
through Beena chat, plus a dedicated admin menu and views.
"""
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_beena_order = fields.Boolean(
        string='Beena Order',
        index=True,
        copy=False,
        help='Set automatically when the quotation was created from the Beena chat.',
    )
    beena_session_id = fields.Char(
        string='Beena Session',
        copy=False,
        index=True,
        help='Chat session identifier that produced this order.',
    )
    beena_created_at = fields.Datetime(
        string='Created via Beena at',
        copy=False,
    )
    beena_customer_phone = fields.Char(
        string='Phone (Beena)',
        copy=False,
        help='Phone collected by Beena during checkout (mirrored to the partner).',
    )
    beena_customer_governorate = fields.Char(
        string='Governorate (Beena)',
        copy=False,
    )
    beena_customer_city = fields.Char(
        string='City (Beena)',
        copy=False,
    )
    beena_customer_street = fields.Char(
        string='Street / Address (Beena)',
        copy=False,
    )
