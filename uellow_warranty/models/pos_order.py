# -*- coding: utf-8 -*-
from odoo import api, models
from .account_move import _flag


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        icp = self.env['ir.config_parameter'].sudo()
        if _flag(icp, 'uellow_warranty.enabled') and _flag(icp, 'uellow_warranty.auto_create_pos'):
            for order in orders:
                order._uellow_create_warranty_cards()
        return orders

    def _uellow_create_warranty_cards(self):
        if not self.partner_id:
            return
        Card = self.env['uellow.warranty.card'].sudo()
        for line in self.lines:
            Card.issue(self.partner_id, line.product_id,
                       date_start=self.date_order.date() if self.date_order else None,
                       pos=self, company=self.company_id)
