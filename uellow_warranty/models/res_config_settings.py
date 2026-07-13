# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uellow_warranty_enabled = fields.Boolean(
        string='Enable warranty engine',
        config_parameter='uellow_warranty.enabled', default=True)
    uellow_warranty_auto_invoice = fields.Boolean(
        string='Auto-issue cards when an invoice is posted',
        config_parameter='uellow_warranty.auto_create_invoice', default=True)
    uellow_warranty_auto_sale = fields.Boolean(
        string='Auto-issue when a sales order is confirmed',
        config_parameter='uellow_warranty.auto_create_sale', default=False)
    uellow_warranty_auto_pos = fields.Boolean(
        string='Auto-issue on POS orders',
        config_parameter='uellow_warranty.auto_create_pos', default=True)
    uellow_warranty_show_docs = fields.Boolean(
        string='Show warranty block on documents',
        config_parameter='uellow_warranty.show_on_documents', default=True)
    uellow_warranty_default_months = fields.Integer(
        string='Default warranty (months)',
        config_parameter='uellow_warranty.default_months', default=12)
    uellow_warranty_mode = fields.Selection(
        [('category', 'By category (with per-product override & default)'),
         ('product', 'Per product only (no warranty unless a product has a policy)')],
        string='Warranty assignment',
        config_parameter='uellow_warranty.assignment_mode', default='category')
