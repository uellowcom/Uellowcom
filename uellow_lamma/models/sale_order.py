# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_lamma = fields.Boolean('Lamma line', default=False,
                              help='This line belongs to a لمّة يلو smart bundle.')
    lamma_type = fields.Char('Lamma type')  # 'normal' | 'installment'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_lamma = fields.Boolean('Has Lamma', compute='_compute_has_lamma')

    def _compute_has_lamma(self):
        for o in self:
            o.has_lamma = any(o.order_line.mapped('is_lamma'))
