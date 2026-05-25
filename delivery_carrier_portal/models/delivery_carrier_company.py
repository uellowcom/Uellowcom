# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DeliveryCarrierCompany(models.Model):
    _name = 'delivery.carrier.company'
    _description = 'Delivery Carrier Company'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Company Name', required=True, tracking=True)
    logo = fields.Binary(string='Logo')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    active = fields.Boolean(default=True, tracking=True)

    cash_settlement_mode = fields.Selection([
        ('per_order', 'Per Order'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Cash Settlement Mode', default='weekly', required=True, tracking=True)

    portal_user_ids = fields.Many2many(
        'res.users', 'carrier_company_portal_users_rel',
        'company_id', 'user_id',
        string='Portal Managers',
        domain="[('share', '=', True)]",
    )
    driver_ids = fields.One2many('delivery.driver', 'carrier_company_id', string='Drivers')
    driver_count = fields.Integer(compute='_compute_driver_count', string='Drivers')

    trip_ids = fields.One2many('delivery.trip', 'carrier_company_id', string='Trips')
    order_ids = fields.One2many('sale.order', 'delivery_carrier_company_id', string='Orders')

    order_count = fields.Integer(compute='_compute_order_count', string='Orders')
    pending_cash = fields.Float(compute='_compute_pending_cash', string='Pending Cash (KD)')

    @api.depends('driver_ids')
    def _compute_driver_count(self):
        for rec in self:
            rec.driver_count = len(rec.driver_ids)

    @api.depends('order_ids')
    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    @api.depends('order_ids.cash_collection_status', 'order_ids.amount_total')
    def _compute_pending_cash(self):
        for rec in self:
            orders = rec.order_ids.filtered(
                lambda o: o.payment_method_type == 'cash'
                and o.cash_collection_status in ('collected', 'pending')
                and o.delivery_status == 'delivered'
            )
            rec.pending_cash = sum(orders.mapped('amount_total'))
    pricing_rule_ids = fields.One2many(
        'carrier.pricing.rule', 'carrier_company_id',
        string='Pricing Rules',
    )
