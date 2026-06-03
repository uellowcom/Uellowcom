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
    # Threading — a reply points at the comment it answers.
    parent_id = fields.Many2one(
        'product.video.comment', string='In reply to',
        ondelete='cascade', index=True)
    reply_ids = fields.One2many('product.video.comment', 'parent_id', string='Replies')
    reply_count = fields.Integer(compute='_compute_reply_count')
    # Marks an official store/admin reply (shown with a badge in the app).
    is_seller = fields.Boolean(string='Store reply', default=False)

    def _compute_reply_count(self):
        for rec in self:
            rec.reply_count = len(rec.reply_ids.filtered('active'))

    def display_author(self):
        self.ensure_one()
        if self.is_seller:
            return self.author_name or 'Uellow'
        return (self.partner_id.name if self.partner_id else None) \
            or self.author_name or 'Guest'
