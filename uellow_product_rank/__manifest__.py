# -*- coding: utf-8 -*-
{
    'name': 'Uellow Product Ranks',
    'summary': 'Amazon-style "Best Seller #N in Category" ranks — computed '
               'daily from real sales, per website, surfaced on product '
               'cards, product pages and builder blocks.',
    'version': '1.0.0',
    'category': 'Sales',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/rank_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
}
