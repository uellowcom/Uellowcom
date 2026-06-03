from odoo import api, fields, models


class ProductVideo(models.Model):
    """Add Bunny Stream (or any S3/CDN-style external host) as a video
    backend so admins can keep large MP4s OFF the Odoo server.

    Admin workflow:
      1. Upload to Bunny Stream via Bunny dashboard.
      2. Copy the video GUID (e.g. 1a2b3c4d-...-...).
      3. Set `video_type = bunny_stream`, paste the GUID in
         `bunny_video_id`. Optionally tick `bunny_thumb_auto` to use
         the auto-generated thumbnail.
      4. Save — `bunny_playback_url` and `bunny_thumb_url` compute
         automatically from system parameters."""
    _inherit = 'product.video'

    video_type = fields.Selection(
        selection_add=[('bunny_stream', 'Bunny Stream (external CDN)')],
        ondelete={'bunny_stream': 'set default'},
    )

    bunny_video_id = fields.Char(
        string='Bunny video GUID',
        help='The video GUID from the Bunny Stream dashboard.',
    )
    bunny_playback_url = fields.Char(
        string='Bunny playback URL (HLS)',
        compute='_compute_bunny_urls', store=False,
    )
    bunny_thumb_url = fields.Char(
        string='Bunny thumbnail URL',
        compute='_compute_bunny_urls', store=False,
    )
    bunny_thumb_auto = fields.Boolean(
        string='Use Bunny auto thumbnail',
        default=True,
        help='If on, the Bunny CDN auto-generates a thumbnail and the '
             'mobile app + website use it. If off, the thumbnail field '
             'on this record is used instead.',
    )

    @api.depends('video_type', 'bunny_video_id')
    def _compute_bunny_urls(self):
        ICP = self.env['ir.config_parameter'].sudo()
        pull = (ICP.get_param('uellow_cdn_video.bunny_pull_zone') or '').strip()
        lib  = (ICP.get_param('uellow_cdn_video.bunny_library_id') or '').strip()
        for rec in self:
            if rec.video_type != 'bunny_stream' or not rec.bunny_video_id or not pull:
                rec.bunny_playback_url = ''
                rec.bunny_thumb_url = ''
                continue
            gid = rec.bunny_video_id.strip()
            rec.bunny_playback_url = f'https://{pull}/{gid}/playlist.m3u8'
            rec.bunny_thumb_url = f'https://{pull}/{gid}/thumbnail.jpg'
