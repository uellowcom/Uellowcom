# -*- coding: utf-8 -*-
{
    'name': 'Uellow — Supplier Price-Update Requests',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'Pick a brand/merchant, print a bilingual price-update list for '
               'suppliers (current/new price + availability), apply prices back.',
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'depends': ['purchase', 'product', 'mail', 'uellow_multivendor',
                'dev_facebook_shop_integration'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/price_request_views.xml',
        'views/portal_price_request.xml',
        'views/res_config_settings_views.xml',
        'report/price_request_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
