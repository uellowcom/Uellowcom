# -*- coding: utf-8 -*-
{
    'name': 'Uellow Home Slider',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'سلايدر الصفحة الرئيسية - يدعم العربية والإنجليزية والموبايل',
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'depends': ['website'],
    'data': [
        'security/ir.model.access.csv',
        'views/slider_views.xml',
        'views/snippets/snippet.xml',
        'data/default_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_home_slider/static/src/css/slider.css',
            'uellow_home_slider/static/src/js/slider.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
