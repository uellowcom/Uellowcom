from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    pr_star_5 = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_star_4 = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_star_3 = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_star_2 = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_star_1 = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_total  = fields.Integer(compute='_compute_pr_stats', store=True)
    pr_avg    = fields.Float(compute='_compute_pr_stats', store=True, digits=(3, 1))

    @api.depends('rating_ids.rating', 'rating_ids.consumed')
    def _compute_pr_stats(self):
        for p in self:
            r = p.rating_ids.filtered(lambda x: x.consumed and x.rating > 0)
            t = len(r)
            p.pr_total = t
            if t:
                v = [x.rating for x in r]
                p.pr_avg    = round(sum(v) / t, 1)
                p.pr_star_5 = sum(1 for x in v if x == 5)
                p.pr_star_4 = sum(1 for x in v if x == 4)
                p.pr_star_3 = sum(1 for x in v if x == 3)
                p.pr_star_2 = sum(1 for x in v if x == 2)
                p.pr_star_1 = sum(1 for x in v if x == 1)
            else:
                p.pr_avg = p.pr_star_5 = p.pr_star_4 = p.pr_star_3 = p.pr_star_2 = p.pr_star_1 = 0
