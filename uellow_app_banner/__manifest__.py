# -*- coding: utf-8 -*-
{
    'name': 'Uellow — Mobile App Smart Banner',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Bilingual "Get the Uellow app" smart banner + download popup.',
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'depends': ['website', 'uellow_theme_common'],
    'data': [
        'views/banner_template.xml',
        'views/popup_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_app_banner/static/src/css/banner.css',
            'uellow_app_banner/static/src/js/banner.js',
            'uellow_app_banner/static/src/css/popup.css',
            'uellow_app_banner/static/src/js/popup.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
