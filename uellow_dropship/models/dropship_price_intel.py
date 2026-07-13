# -*- coding: utf-8 -*-
"""Dropship price intelligence — track each product's PROVIDER cost over time.

Unlike the Smart-Connector competitor tracker (external URLs), this watches the
supplier's own cost: every time a price sync sees the provider cost move, it
logs a history row and re-evaluates the margin, so we catch cost spikes that
would erode (or wipe) the margin before a customer buys at a loss.
Provider-agnostic: the cost comes from each product's own provider adapter.
"""
from odoo import fields, models


class DropshipPriceHistory(models.Model):
    _name = 'dropship.price.history'
    _description = 'Dropship Price History'
    _order = 'create_date desc'

    product_id = fields.Many2one('dropship.product', required=True,
                                 ondelete='cascade', index=True)
    old_cost = fields.Float(string="Old Cost")
    new_cost = fields.Float(string="New Cost")
    change_pct = fields.Float(string="Cost Change %")
    sale_price = fields.Float(string="Sale Price")
    margin_pct = fields.Float(string="Margin %")
    currency_code = fields.Char(string="Cost Ccy")
    note = fields.Char()
