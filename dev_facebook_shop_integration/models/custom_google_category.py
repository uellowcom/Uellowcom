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

class CustomGoogleCategory(models.Model):
    _name = 'custom.google.category'
    _description = "Google Category"

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(index=True)
    code = fields.Char(
        string='Code',
        required=True,
    )
    parent_id = fields.Many2one(
        comodel_name='custom.google.category',
        string='Parent',
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_id = fields.One2many(
        'custom.google.category',
        'parent_id',
        string='Children Categories',
    )
    parents_and_self = fields.Many2many(
        'custom.google.category',
        compute='_compute_full_parent_path',
    )

    @api.constrains('parent_id')
    def _check_no_recursive_parent(self):
        if not self._check_recursion():
            raise ValueError(_(
                'Error ! You cannot create recursive categories.'))

    @api.constrains('code')
    def _check_unique_code(self):
        for category in self:
            recs = self.search_count([('code', '=', category.code)])
            if recs > 1:
                raise ValidationError(_(
                    'The code of the Google category must be unique.'))

    def name_get(self):
        res = []
        for category in self:
            res.append((category.id, " > ".join(
                category.parents_and_self.mapped('name'))))
        return res

    def unlink(self):
        self.child_id.parent_id = None
        return super(CustomGoogleCategory, self).unlink()

    def _compute_full_parent_path(self):
        for category in self:
            if category.parent_path:
                category.parents_and_self = self.env['custom.google.category'].browse(
                    [int(p) for p in category.parent_path.split('/')[:-1]])
            else:
                category.parents_and_self = category

    def fetch_google_categories(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fetch Google Categories',
            'res_model': 'facebook.google.category',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_platform': 'google',
                'default_url': 'https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt',
            }
        }
