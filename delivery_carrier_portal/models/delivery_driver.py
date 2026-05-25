# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DeliveryDriver(models.Model):
    _name = 'delivery.driver'
    _description = 'Delivery Driver'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Driver Name', required=True)
    phone = fields.Char(string='Phone', required=True)
    photo = fields.Binary(string='Photo')
    vehicle_info = fields.Char(string='Vehicle Info')
    can_send_payment_link = fields.Boolean(
        string='Can Send Payment Links',
        default=False,
        help='Allow this driver to generate and send payment links to customers',
    )
    carrier_company_id = fields.Many2one(
        'delivery.carrier.company', string='Carrier Company',
        required=True, ondelete='cascade',
    )
    portal_user_id = fields.Many2one(
        'res.users', string='Portal User',
        domain="[('share', '=', True)]",
    )
    active = fields.Boolean(default=True)
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], default='active', tracking=True)

    trip_line_ids = fields.One2many('delivery.trip.line', 'driver_id', string='Deliveries')
    delivery_count = fields.Integer(compute='_compute_delivery_count')

    @api.depends('trip_line_ids')
    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = len(rec.trip_line_ids)
