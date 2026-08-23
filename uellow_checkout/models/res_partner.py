# -*- coding: utf-8 -*-
from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @staticmethod
    def _uc_trim(vals):
        for f in ('email', 'phone', 'mobile'):
            v = vals.get(f)
            if isinstance(v, str):
                vals[f] = v.strip()
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            self._uc_trim(v)
        return super().create(vals_list)

    def write(self, vals):
        self._uc_trim(vals)
        return super().write(vals)
