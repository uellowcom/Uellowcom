# -*- coding: utf-8 -*-
from odoo import fields, models


def _flag(icp, key, default='True'):
    return icp.get_param(key, default) in ('True', 'true', '1', True)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        icp = self.env['ir.config_parameter'].sudo()
        if _flag(icp, 'uellow_warranty.enabled') and _flag(icp, 'uellow_warranty.auto_create_invoice'):
            for move in posted.filtered(lambda m: m.move_type == 'out_invoice'):
                move._uellow_create_warranty_cards()
        return posted

    def _uellow_create_warranty_cards(self):
        Card = self.env['uellow.warranty.card'].sudo()
        for line in self.invoice_line_ids:
            if line.display_type and line.display_type not in ('product',):
                continue
            Card.issue(self.partner_id, line.product_id,
                       date_start=self.invoice_date or fields.Date.context_today(self),
                       invoice=self, company=self.company_id)
