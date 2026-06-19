# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    uellow_delivery_terms = fields.Char(
        related='company_id.uellow_delivery_terms', readonly=False)
    uellow_warranty_terms = fields.Char(
        related='company_id.uellow_warranty_terms', readonly=False)
    uellow_returns_terms = fields.Char(
        related='company_id.uellow_returns_terms', readonly=False)
    uellow_payment_terms_note = fields.Char(
        related='company_id.uellow_payment_terms_note', readonly=False)
    uellow_doc_footer = fields.Char(
        related='company_id.uellow_doc_footer', readonly=False)
    uellow_bank_line = fields.Char(
        related='company_id.uellow_bank_line', readonly=False)
