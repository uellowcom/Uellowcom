# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_video_ids = fields.One2many(
        'product.video',
        'product_tmpl_id',
        string='Product Videos',
    )
    has_product_video = fields.Boolean(
        string='Has Video',
        compute='_compute_has_product_video',
        store=True,
        index=True,
    )
    video_count = fields.Integer(
        string='Video Count',
        compute='_compute_has_product_video',
        store=True,
    )

    @api.depends('product_video_ids', 'product_video_ids.active')
    def _compute_has_product_video(self):
        for tmpl in self:
            videos = tmpl.product_video_ids.filtered(lambda v: v.active)
            tmpl.video_count = len(videos)
            tmpl.has_product_video = bool(videos)

    def get_first_video_data(self):
        """Return the first active video data dict for frontend."""
        self.ensure_one()
        video = self.product_video_ids.filtered(lambda v: v.active)
        if video:
            return video[0].get_video_data()
        return None
