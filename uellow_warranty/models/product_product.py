# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Bilingual names exposed to the POS receipt (independent of POS language).
    pos_name_en = fields.Char(compute='_compute_pos_names', store=True)
    pos_name_ar = fields.Char(compute='_compute_pos_names', store=True)

    @api.depends('name')
    def _compute_pos_names(self):
        for p in self:
            en = p.with_context(lang='en_US').name
            ar = p.with_context(lang='ar_001').name
            p.pos_name_en = en
            p.pos_name_ar = ar if (ar and ar != en) else False

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ('pos_name_en', 'pos_name_ar'):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
