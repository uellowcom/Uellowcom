# -*- coding: utf-8 -*-
"""product.video.comment — comments on Reels videos.

Deliberately SEPARATE from product reviews (`rating.rating` / review models):
these are short social comments on the video itself (TikTok-style), with their
own backend menu + analytics, and never mix with star reviews.
"""
from odoo import api, fields, models


class ProductVideoComment(models.Model):
    _name = 'product.video.comment'
    _description = 'Reels Video Comment'
    _order = 'create_date desc'

    video_id = fields.Many2one(
        'product.video', string='Video', required=True,
        ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product',
        related='video_id.product_tmpl_id', store=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Author', index=True)
    author_name = fields.Char(string='Author name')
    body = fields.Text(string='Comment', required=True)
    likes = fields.Integer(string='Likes', default=0)
    active = fields.Boolean(default=True)

    def display_author(self):
        self.ensure_one()
        return (self.partner_id.name if self.partner_id else None) \
            or self.author_name or 'Guest'
