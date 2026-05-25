# -*- coding: utf-8 -*-
{
    'name': 'Uellow Checkout',
    'version': '18.0.2.7.0',
    'summary': 'App-style checkout — Fast Buy design',
    'author': 'Uellow',
    'category': 'Website/eCommerce',
    'depends': ['website_sale', 'delivery', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'views/backend_views.xml',
        'views/assets.xml',
        'views/checkout_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_checkout/static/src/css/checkout.css',
            'uellow_checkout/static/src/js/checkout.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
