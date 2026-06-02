# -*- coding: utf-8 -*-
"""Tiny extras to the existing delivery.driver model used by the API."""
from odoo import fields, models


class DeliveryDriverExtras(models.Model):
    _inherit = 'delivery.driver'

    # Preferred app language. Independent of the user's Odoo lang so the
    # driver can pick AR even if the portal account is EN.
    app_lang = fields.Char(default='en_US')
    # JSON blob for notification prefs (push categories, sound on/off).
    notif_prefs_json = fields.Text(default='{}')
