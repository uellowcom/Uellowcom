# -*- coding: utf-8 -*-
{
    'name': 'Uellow — Mobile App Smart Banner',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Bilingual "Get the Uellow app" banner shown on mobile UAs only.',
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'depends': ['website'],
    'data': [
        'views/banner_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_app_banner/static/src/css/banner.css',
            'uellow_app_banner/static/src/js/banner.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
