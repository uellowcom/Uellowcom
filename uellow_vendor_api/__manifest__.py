# -*- coding: utf-8 -*-
{
    'name': 'Uellow Vendor API',
    'version': '18.0.1.0.0',
    'summary': 'Mobile vendor app backend — store, products, orders, payouts, reviews, chat',
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    'category': 'Sales/Sales',
    'depends': [
        'base', 'mail', 'sale_management', 'stock', 'website', 'payment',
        'uellow_multivendor',
    ],
    'data': ['security/ir.model.access.csv'],
    'installable': True,
    'application': False,
}
