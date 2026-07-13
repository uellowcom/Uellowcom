# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WarrantyClaim(models.Model):
    _name = 'uellow.warranty.claim'
    _description = 'Warranty Claim'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Claim No.', default='New', copy=False, readonly=True, index=True)
    card_id = fields.Many2one('uellow.warranty.card', string='Warranty', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='card_id.partner_id', store=True, string='Customer')
    product_id = fields.Many2one(related='card_id.product_id', store=True, string='Product')
    date = fields.Date(string='Claim date', default=fields.Date.context_today)
    issue = fields.Text(string='Reported issue', required=True)
    state = fields.Selection(
        [('new', 'New'), ('approved', 'Approved'),
         ('rejected', 'Rejected'), ('resolved', 'Resolved')],
        default='new', tracking=True)
    resolution = fields.Text(string='Resolution')
    company_id = fields.Many2one(related='card_id.company_id', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uellow.warranty.claim') or 'WCLM/0001'
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_resolve(self):
        self.write({'state': 'resolved'})
