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
        help='The Stream LIBRARY API key (Bunny dashboard → Stream → your '
             'library → API). NOT the account-level key.',
    )
    bunny_delete_local_after_upload = fields.Boolean(
        string='Delete local file after upload',
        config_parameter='uellow_cdn_video.bunny_delete_local_after_upload',
        default=True,
        help='Remove the uploaded MP4 from Odoo once it is safely on Bunny, '
             'to reclaim server storage. Turn off to keep a local backup.',
    )
    bunny_auto_sync_stats = fields.Boolean(
        string='Auto-refresh video analytics daily',
        config_parameter='uellow_cdn_video.bunny_auto_sync_stats',
        default=True,
        help='Run a daily job that pulls views / watch-time / status from '
             'Bunny into the Product Videos dashboard.',
    )
