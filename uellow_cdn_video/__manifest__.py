{
    'name': 'Uellow — CDN Video (Bunny Stream)',
    'version': '18.0.1.0.0',
    'summary': 'Self-hosted product videos via Bunny Stream — admin uploads to Bunny, pastes the video ID in Odoo, the mobile app + website stream HLS from the CDN with zero load on the Odoo server.',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['uellow_tiktok_video'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_video_views.xml',
        'views/product_video_actions.xml',
        'views/video_comment_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
