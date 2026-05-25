# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    condition = fields.Selection([('new', 'New'), ('refurbished', 'Refurbished'), ('used', 'Used')], default="new")
    brand_id = fields.Many2one('product.brand',string='Brand')
    facebook_category_id = fields.Many2one('custom.facebook.category', string='Facebook Category')
    google_category_id = fields.Many2one('custom.google.category', string='Google Category')
    gtin = fields.Char(string='GTIN')
    mpn = fields.Char(string='MPN')


class Product(models.Model):
    _inherit = 'product.product'

    condition = fields.Selection([('new', 'New'), ('refurbished', 'Refurbished'), ('used', 'Used')], default="new")
    brand_id = fields.Many2one('product.brand',string='Brand')
    facebook_category_id = fields.Many2one('custom.facebook.category', string='Facebook Category')
    google_category_id = fields.Many2one('custom.google.category', string='Google Category')
    gtin = fields.Char(string='GTIN')
    mpn = fields.Char(string='MPN')
