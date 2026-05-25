# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductVideo(models.Model):
    _name = 'product.video'
    _description = 'Product TikTok / Direct Video'
    _order = 'sequence, id'

    name = fields.Char(string='Video Title', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        required=True,
        ondelete='cascade',
        index=True,
    )
    video_type = fields.Selection([
        ('tiktok_url', 'TikTok URL'),
        ('direct_upload', 'Direct Upload (MP4/WebM)'),
        ('youtube', 'YouTube'),
        ('vimeo', 'Vimeo'),
    ], string='Video Type', required=True, default='tiktok_url')

    # TikTok URL
    tiktok_url = fields.Char(string='TikTok URL')
    tiktok_video_id = fields.Char(string='TikTok Video ID', compute='_compute_tiktok_video_id', store=True)
    tiktok_embed_html = fields.Text(string='TikTok Embed HTML', compute='_compute_tiktok_embed', store=False)

    # Direct upload
    video_file = fields.Binary(string='Video File', attachment=True)
    video_filename = fields.Char(string='Video Filename')
    video_mimetype = fields.Char(string='MIME Type', default='video/mp4')

    # Other platforms
    video_url = fields.Char(string='Video URL (YouTube/Vimeo)')

    # Thumbnail
    thumbnail = fields.Image(string='Thumbnail', max_width=800, max_height=800)
    auto_thumbnail = fields.Boolean(string='Use Auto-Generated Thumbnail', default=True)

    # Computed embed
    embed_url = fields.Char(string='Embed URL', compute='_compute_embed_url', store=False)

    active = fields.Boolean(default=True)

    @api.depends('tiktok_url')
    def _compute_tiktok_video_id(self):
        """Extract TikTok video ID from various TikTok URL formats."""
        for rec in self:
            rec.tiktok_video_id = False
            if rec.tiktok_url:
                url = rec.tiktok_url.strip()
                # Patterns:
                # https://www.tiktok.com/@username/video/1234567890
                # https://vm.tiktok.com/XXXXXX/  (short link - needs resolve)
                # https://vt.tiktok.com/XXXXXX/
                pattern = r'tiktok\.com/@[\w.]+/video/(\d+)'
                match = re.search(pattern, url)
                if match:
                    rec.tiktok_video_id = match.group(1)
                else:
                    # Short URL - store as-is and resolve on frontend
                    rec.tiktok_video_id = 'short:' + url

    @api.depends('tiktok_url', 'tiktok_video_id')
    def _compute_tiktok_embed(self):
        for rec in self:
            if rec.tiktok_video_id and not rec.tiktok_video_id.startswith('short:'):
                rec.tiktok_embed_html = f"""
                    <blockquote class="tiktok-embed" cite="{rec.tiktok_url}"
                        data-video-id="{rec.tiktok_video_id}"
                        style="max-width:605px;min-width:325px;">
                    </blockquote>
                    <script async src="https://www.tiktok.com/embed.js"></script>
                """
            else:
                rec.tiktok_embed_html = False

    @api.depends('video_type', 'tiktok_video_id', 'video_url')
    def _compute_embed_url(self):
        for rec in self:
            rec.embed_url = False
            if rec.video_type == 'tiktok_url' and rec.tiktok_video_id:
                vid_id = rec.tiktok_video_id
                if not vid_id.startswith('short:'):
                    rec.embed_url = f'https://www.tiktok.com/embed/v2/{vid_id}'
            elif rec.video_type == 'youtube' and rec.video_url:
                yt_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', rec.video_url)
                if yt_match:
                    rec.embed_url = f'https://www.youtube.com/embed/{yt_match.group(1)}?autoplay=1'
            elif rec.video_type == 'vimeo' and rec.video_url:
                vm_match = re.search(r'vimeo\.com/(\d+)', rec.video_url)
                if vm_match:
                    rec.embed_url = f'https://player.vimeo.com/video/{vm_match.group(1)}?autoplay=1'

    @api.constrains('tiktok_url', 'video_type')
    def _check_tiktok_url(self):
        for rec in self:
            if rec.video_type == 'tiktok_url' and rec.tiktok_url:
                if 'tiktok.com' not in rec.tiktok_url:
                    raise ValidationError(_('Please enter a valid TikTok URL (must contain tiktok.com)'))

    def get_video_data(self):
        """Return serializable dict for frontend use."""
        self.ensure_one()
        data = {
            'id': self.id,
            'name': self.name,
            'type': self.video_type,
            'embed_url': self.embed_url or '',
            'tiktok_video_id': self.tiktok_video_id or '',
            'tiktok_url': self.tiktok_url or '',
            'has_thumbnail': bool(self.thumbnail),
        }
        if self.video_type == 'direct_upload' and self.video_file:
            data['file_url'] = f'/web/content/product.video/{self.id}/video_file/{self.video_filename or "video.mp4"}'
            data['mimetype'] = self.video_mimetype or 'video/mp4'
        return data
