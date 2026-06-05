from odoo import models, fields

class RatingRating(models.Model):
    _inherit = 'rating.rating'
    review_title = fields.Char(string='Review Title')
    is_verified_purchase = fields.Boolean(default=False)
    helpful_count = fields.Integer(default=0)
    review_image_ids = fields.One2many('rating.review.image', 'rating_id')

    def action_approve(self):
        self.write({'consumed': True})

    def action_reject(self):
        self.write({'consumed': False})

    def write(self, vals):
        """Keep the uellow.product.review twin (archive module) in step
        whenever a review is published/unpublished here — whether via the
        Approve button or the list's Published toggle."""
        res = super().write(vals)
        if 'consumed' in vals:
            Review = self.env.get('uellow.product.review')
            if Review is not None:
                for r in self.filtered(
                        lambda x: x.res_model == 'product.template'):
                    twin = Review.sudo().search([
                        ('product_id', '=', r.res_id),
                        ('partner_id', '=', r.partner_id.id),
                    ], limit=1)
                    if twin:
                        twin.state = 'approved' if vals['consumed'] \
                            else 'pending'
        return res


class RatingReviewImage(models.Model):
    _name = 'rating.review.image'
    _description = 'Review Image'
    _order = 'sequence, id'
    rating_id = fields.Many2one('rating.rating', ondelete='cascade', required=True)
    sequence = fields.Integer(default=10)
    image = fields.Binary(attachment=True)
    image_filename = fields.Char()
    mimetype = fields.Char()
    name = fields.Char()
