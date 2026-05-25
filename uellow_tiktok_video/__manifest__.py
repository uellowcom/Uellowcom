# -*- coding: utf-8 -*-
{
    'name': 'Uellow TikTok Video Gallery',
    'version': '18.0.1.0.0',
    'summary': 'Add TikTok video support to product gallery in Odoo 18 Website',
    'description': """
        Extends Odoo 18 product gallery to support TikTok videos.
        - Upload TikTok videos directly or via URL
        - Show video first in product gallery
        - Display play icon overlay on product images in shop listings
    """,
    'category': 'Website/eCommerce',
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'depends': [
        'website_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'uellow_tiktok_video/static/src/js/product_video_backend.js',
            'uellow_tiktok_video/static/src/css/product_video_backend.css',
        ],
        'web.assets_frontend': [
            'uellow_tiktok_video/static/src/js/product_video_frontend.js',
            'uellow_tiktok_video/static/src/js/product_video_modal.js',
            'uellow_tiktok_video/static/src/css/product_video_frontend.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
