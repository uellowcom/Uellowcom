from odoo import models, fields, api


class ReviewConfig(models.Model):
    _name = 'uellow.review.config'
    _description = 'Review Incentive Configuration'

    name = fields.Char(default='Review Settings')
    active = fields.Boolean(default=True)
    require_purchase = fields.Boolean('Require Verified Purchase', default=True)
    auto_approve = fields.Boolean('Auto-approve Reviews', default=False)
    points_text = fields.Integer('Points for Text Review', default=5)
    points_photo = fields.Integer('Points for Photo Review', default=15)
    points_video = fields.Integer('Points for Video Review', default=30)
    min_review_length = fields.Integer('Min Review Length (chars)', default=20)
    max_rating = fields.Integer('Max Rating Stars', default=5)
    moderation_required = fields.Boolean('Moderation Required', default=True)

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
        return cfg
