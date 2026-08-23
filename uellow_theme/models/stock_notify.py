# -*- coding: utf-8 -*-
from odoo import models, fields, api


class UellowStockNotify(models.Model):
    _name = 'uellow.stock.notify'
    _description = 'Back-in-stock notification request'
    _order = 'create_date desc'
    _rec_name = 'contact'

    product_tmpl_id = fields.Many2one(
        'product.template', string='المنتج', required=True,
        ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='المتغيّر', ondelete='cascade')
    contact = fields.Char('جهة الاتصال', required=True, index=True)
    is_email = fields.Boolean('بريد؟', compute='_compute_is_email', store=True)
    partner_id = fields.Many2one('res.partner', string='العميل')
    website_id = fields.Many2one('website', string='الموقع')
    lang = fields.Char('اللغة')
    state = fields.Selection(
        [('new', 'بانتظار التوفّر'), ('notified', 'تم الإعلام')],
        default='new', string='الحالة', index=True)
    notified_date = fields.Datetime('تاريخ الإعلام')

    @api.depends('contact')
    def _compute_is_email(self):
        for r in self:
            r.is_email = '@' in (r.contact or '')
