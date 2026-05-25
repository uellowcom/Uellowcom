# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
from odoo import models, fields, _


class ShopFields(models.Model):
    _name = 'shop.fields'
    _description = "Shop Fields"

    name = fields.Char('Name')
    facebook_feed_id = fields.Many2one('facebook.product.data.feed', string='Facebook Feed')
    field_id = fields.Many2one('ir.model.fields', string='Field')
