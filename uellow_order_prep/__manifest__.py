# -*- coding: utf-8 -*-
{
    'name': 'Uellow Order Preparation',
    'summary': 'Warehouse order-preparation workflow inside Sales '
               '(تجهيز الطلبات) — prepare, mark ready for pickup, print '
               'label / invoice / warranty from the order screen.',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': [
        'sale_stock',
        'account',
        'delivery_carrier_portal',
        'uellow_warranty',
        'delivery_label',
    ],
    'data': [
        'views/order_prep_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
