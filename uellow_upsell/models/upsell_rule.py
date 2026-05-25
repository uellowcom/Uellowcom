from odoo import models, fields, api


class UpsellRule(models.Model):
    _name = 'uellow.upsell.rule'
    _description = 'Upsell/Cross-sell Rule'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    rule_type = fields.Selection([
        ('upsell',    'Upsell'),
        ('crosssell', 'Cross-sell'),
        ('bundle',    'Bundle'),
    ], required=True, default='crosssell')

    trigger_product_ids = fields.Many2many(
        'product.template', 'upsell_trigger_rel', 'rule_id', 'product_id',
        string='Trigger Products',
    )
    trigger_category_ids = fields.Many2many('product.category', string='Trigger Categories')
    recommended_product_ids = fields.Many2many(
        'product.template', 'upsell_rec_rel', 'rule_id', 'product_id',
        string='Recommended Products',
    )
    display_position = fields.Selection([
        ('product_page', 'Product Page'),
        ('cart',         'Cart'),
        ('both',         'Both'),
    ], default='product_page')
    max_display = fields.Integer('Max Items', default=4)
    discount_bundle = fields.Float('Bundle Discount (%)', default=0.0)
    click_count = fields.Integer(default=0, readonly=True)
    convert_count = fields.Integer(default=0, readonly=True)

    @api.model
    def get_recommendations(self, product_id, rule_type='crosssell', limit=4):
        product = self.env['product.template'].browse(product_id)
        if not product.exists():
            return []
        rules = self.search([('active', '=', True), ('rule_type', '=', rule_type)])
        recommended = self.env['product.template']
        for rule in rules:
            if product in rule.trigger_product_ids or product.categ_id in rule.trigger_category_ids:
                recommended |= rule.recommended_product_ids
        return recommended[:limit].read(['id', 'name', 'list_price', 'website_url'])
