# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WarrantyPolicy(models.Model):
    _name = 'uellow.warranty.policy'
    _description = 'Warranty Policy'
    _order = 'sequence, id'

    name = fields.Char(string='Policy name', required=True)
    name_ar = fields.Char(string='Arabic name')
    icon = fields.Char(string='Icon', default='🛡️',
                       help='Emoji/badge shown for this warranty duration.')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color')
    duration_months = fields.Integer(
        string='Duration (months)', default=12, required=True)
    coverage_en = fields.Text(
        string='Coverage (EN)',
        default='Covers manufacturing defects under normal use. '
                'Excludes physical/water damage and misuse.')
    coverage_ar = fields.Text(
        string='Coverage (AR)',
        default='يغطي عيوب التصنيع تحت الاستخدام الطبيعي. '
                'لا يشمل الكسر أو ضرر المياه أو سوء الاستخدام.')
    terms_en = fields.Text(string='Full terms (EN)')
    terms_ar = fields.Text(string='Full terms (AR)')
    category_ids = fields.Many2many(
        'product.category', string='Applicable categories',
        help='Products in these categories use this policy. Leave empty for the default policy.')
    is_default = fields.Boolean(string='Default policy')
    website_id = fields.Many2one(
        'website', string='Website',
        help='Scope this policy to one website/country. Leave empty to apply to all websites.')
    no_warranty = fields.Boolean(
        string='No warranty (returns only)',
        help='Consumables etc. — no warranty card is auto-issued for these categories.')
    card_count = fields.Integer(compute='_compute_card_count', string='Cards')

    def _compute_card_count(self):
        Card = self.env['uellow.warranty.card']
        groups = Card._read_group(
            [('policy_id', 'in', self.ids)], ['policy_id'], ['__count'])
        mapped = {p.id: c for p, c in groups}
        for rec in self:
            rec.card_count = mapped.get(rec.id, 0)

    @api.model
    def _get_for_product(self, product, website=None):
        """Resolve policy honouring assignment mode + website scope.
        Website-specific policies win over global ones.
        mode='product' -> only the product's own policy (no fallback).
        mode='category' -> product override -> category match -> default."""
        tmpl = product.product_tmpl_id
        if tmpl.warranty_policy_id:
            return tmpl.warranty_policy_id
        mode = self.env['ir.config_parameter'].sudo().get_param(
            'uellow_warranty.assignment_mode', 'category')
        if mode == 'product':
            return self.browse()
        wid = website.id if website else False
        categ = product.categ_id
        cat_ids = []
        while categ:
            cat_ids.append(categ.id)
            categ = categ.parent_id
        # category match: website-specific first, then global
        if cat_ids:
            if wid:
                pol = self.search([('category_ids', 'in', cat_ids),
                                   ('website_id', '=', wid)], order='sequence', limit=1)
                if pol:
                    return pol
            pol = self.search([('category_ids', 'in', cat_ids),
                               ('website_id', '=', False)], order='sequence', limit=1)
            if pol:
                return pol
        # default: website-specific first, then global
        if wid:
            d = self.search([('is_default', '=', True), ('website_id', '=', wid)], limit=1)
            if d:
                return d
        return (self.search([('is_default', '=', True), ('website_id', '=', False)], limit=1)
                or self.search([('website_id', '=', False)], order='sequence', limit=1))

    def action_view_cards(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warranty Cards',
            'res_model': 'uellow.warranty.card',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'default_policy_id': self.id},
        }
