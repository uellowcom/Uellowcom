# -*- coding: utf-8 -*-
"""Label the World country→website mapping in the app's country picker as
"China / الصين" with the 🇨🇳 flag. The mapping is attached to the real China
country so geo/routing stay valid; here we just pin the picker label + flag
(and English as the default pick) regardless of stored translations.
"""
from odoo import models


class MobileCountryWebsite(models.Model):
    _inherit = 'mobile.country.website'

    def to_dict(self):
        d = super().to_dict()
        try:
            wid = int(self.env['ir.config_parameter'].sudo()
                      .get_param('uellow_dropship.website_id') or 0)
        except Exception:  # noqa: BLE001
            wid = 0
        if wid and self.website_id.id == wid:
            d['country']['name'] = {'en': 'China', 'ar': 'الصين'}
            d['country']['flag'] = '🇨🇳'
            # China buyers browse in English by default
            d['default_language'] = d.get('default_language') or 'en_US'
            # Uellow World is priced with USD as the BASE reference currency;
            # in-store every price is converted to the visitor's own currency by
            # geo-IP (see app_bridge._world_currency). So the picker/settings
            # must show USD as the World base, not the website's KWD company
            # currency (which wrongly read "KWD" next to China).
            d['currency'] = 'USD'
            d['currency_symbol'] = '$'
        return d
