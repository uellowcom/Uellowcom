# -*- coding: utf-8 -*-
"""Vendor product file imports (v2.1.69) — the portal upload at
/my/vendor/products/import stores the file here; an admin reviews and
processes it from Marketplace ▸ Product Imports."""
from odoo import fields, models


class UellowProductImport(models.Model):
    _name = 'uellow.product.import'
    _description = 'Vendor Product Import File'
    _order = 'create_date desc'

    vendor_id = fields.Many2one('uellow.vendor', string='Vendor',
                                required=True, index=True,
                                ondelete='cascade')
    file_name = fields.Char('File Name')
    file_data = fields.Binary('File', attachment=True)
    state = fields.Selection([
        ('pending', 'Pending Review'),
        ('done', 'Imported'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True, index=True)
    note = fields.Char('Admin Note')

    def action_mark_done(self):
        self.write({'state': 'done'})

    def action_reject(self):
        self.write({'state': 'rejected'})
