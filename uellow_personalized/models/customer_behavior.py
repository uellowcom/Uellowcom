from odoo import models, fields


class CustomerBehavior(models.Model):
    _name = 'uellow.customer.behavior'
    _description = 'Customer Behavior Profile'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    recently_viewed_ids = fields.Many2many(
        'product.template', 'behavior_viewed_rel', 'behavior_id', 'product_id',
        string='Recently Viewed',
    )
    preferred_category_ids = fields.Many2many('product.category', string='Preferred Categories')
    last_visit = fields.Datetime('Last Visit')
    visit_count = fields.Integer(default=0)
    country_id = fields.Many2one('res.country')

    _sql_constraints = [('unique_partner', 'UNIQUE(partner_id)', 'Already exists.')]

    def record_view(self, product_id):
        product = self.env['product.template'].browse(product_id)
        if product.exists() and product not in self.recently_viewed_ids:
            self.write({'recently_viewed_ids': [(4, product.id)]})
            if len(self.recently_viewed_ids) > 20:
                self.write({'recently_viewed_ids': [(3, self.recently_viewed_ids[0].id)]})
