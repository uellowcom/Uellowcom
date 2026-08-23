# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosSession(models.Model):
    _inherit = "pos.session"

    x_profit = fields.Monetary(
        string="الربح", compute="_compute_x_margin", store=True,
        currency_field="currency_id",
        help="إجمالي ربح الجلسة = مجموع (سعر البيع − التكلفة) لبنود الطلبات.")
    x_margin_pct = fields.Float(
        string="المارجن %", compute="_compute_x_margin", store=True,
        aggregator="avg",
        help="نسبة الربح إلى صافي المبيعات (متوسط على مستوى المجموعة).")

    @api.depends("order_ids", "order_ids.lines.price_subtotal",
                 "order_ids.lines.total_cost")
    def _compute_x_margin(self):
        for s in self:
            lines = s.order_ids.mapped("lines")
            sales = sum(lines.mapped("price_subtotal"))
            cost = sum(lines.mapped("total_cost"))
            s.x_profit = sales - cost
            s.x_margin_pct = ((sales - cost) / sales * 100.0) if sales else 0.0
