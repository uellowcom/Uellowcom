from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bunny_stream_library_id = fields.Char(
        string='Bunny Stream — Library ID',
        config_parameter='uellow_cdn_video.bunny_library_id',
        help='Numeric ID of your Bunny Stream library (Bunny dashboard → '
             'Stream → your library → Settings).',
    )
    bunny_stream_pull_zone = fields.Char(
        string='Bunny Stream — CDN hostname',
        config_parameter='uellow_cdn_video.bunny_pull_zone',
        help='The .b-cdn.net hostname for your Stream library — e.g. '
             '"vz-12345-abc.b-cdn.net".',
    )
    bunny_stream_api_key = fields.Char(
        string='Bunny Stream — API key',
        config_parameter='uellow_cdn_video.bunny_api_key',
        help='Library access key (used only when we trigger server-side '
             'transcoding / thumbnail fetch — not exposed to clients).',
    )
