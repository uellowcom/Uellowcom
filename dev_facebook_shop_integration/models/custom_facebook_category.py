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
from odoo.exceptions import ValidationError

class CustomFacebookCategory(models.Model):
    _name = 'custom.facebook.category'
    _description = "Facebook Category"


    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
        readonly=True,
    )

    @api.constrains('code')
    def _check_unique_code(self):
        for category in self:
            if self.search_count([('code', '=', category.code)]) > 1:
                raise ValidationError(
                    _('The code of the Facebook category must be unique.'))

    def fetch_facebook_categories(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Facebook Categories',
            'res_model': 'facebook.google.category',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_platform': 'facebook',
                'default_url': 'https://www.facebook.com/products/categories/en_US.txt',
            }
        }
