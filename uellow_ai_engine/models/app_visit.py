# -*- coding: utf-8 -*-
# Analytics for the public /app landing page: one row per visit and per
# store conversion, with platform + country, to power the /app/stats dashboard.
from odoo import models, fields, api


class AppVisit(models.Model):
    _name = 'uellow.app.visit'
    _description = 'App Landing Page Visit / Conversion'
    _order = 'create_date desc'

    action = fields.Selection([
        ('visit', 'Visit'),
        ('conversion', 'Conversion'),
    ], default='visit', index=True)
    platform = fields.Selection([
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('huawei', 'Huawei'),
        ('desktop', 'Desktop'),
        ('other', 'Other'),
    ], index=True)
    store = fields.Selection([
        ('appstore', 'App Store'),
        ('play', 'Google Play'),
        ('huawei', 'AppGallery'),
    ], index=True)
    country_code = fields.Char(index=True)
    country_name = fields.Char()
    user_agent = fields.Char()
    referrer = fields.Char()
    ip_hash = fields.Char(help="Salted hash of the visitor IP (no raw IP stored).")
