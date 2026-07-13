# -*- coding: utf-8 -*-
from odoo import fields, models
from .account_move import _flag


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    warranty_card_ids = fields.One2many('uellow.warranty.card', 'sale_id', string='Warranties')
    warranty_card_count = fields.Integer(compute='_compute_warranty_card_count')

    def _compute_warranty_card_count(self):
        for o in self:
            o.warranty_card_count = len(o.warranty_card_ids)

    def action_confirm(self):
        res = super().action_confirm()
        icp = self.env['ir.config_parameter'].sudo()
        if _flag(icp, 'uellow_warranty.enabled') and _flag(icp, 'uellow_warranty.auto_create_sale', default='False'):
            for order in self:
                order._uellow_create_warranty_cards()
        return res

    def _uellow_create_warranty_cards(self):
        Card = self.env['uellow.warranty.card'].sudo()
        for line in self.order_line:
            if line.display_type:
                continue
            Card.issue(self.partner_id, line.product_id,
                       sale=self, company=self.company_id)

    def action_view_warranties(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warranties',
            'res_model': 'uellow.warranty.card',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
        }
