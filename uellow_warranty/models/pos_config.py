# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    uellow_receipt_warranty = fields.Boolean(
        string='Show warranty on receipt', default=True,
        help='Print the warranty block on the POS receipt.')
    uellow_receipt_warranty_note = fields.Char(
        string='Warranty receipt note',
        default='Warranty included — keep this receipt to activate · ضمان شامل — احتفظ بالفاتورة للتفعيل')


class ResCompany(models.Model):
    _inherit = 'res.company'

    uellow_name_ar = fields.Char(
        string='Company name (Arabic)', default='شركة يلو دوت كوم',
        help='Arabic company name shown on the POS receipt header.')

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ('street', 'city', 'country_id', 'uellow_name_ar'):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ('street', 'city', 'phone', 'email'):
            if f not in fields_list:
                fields_list.append(f)
        return fields_list
