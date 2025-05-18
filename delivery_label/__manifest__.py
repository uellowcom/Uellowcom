# -*- coding: utf-8 -*-
{
    'name': 'Delivery Label',
    'version': '1.0',
    'category': 'Inventory/Delivery',
    'summary': 'Custom delivery carrier labels for sales and stock',
    'description': """
Delivery Label Module
====================
This module adds custom delivery carriers to be configured in the sales module
and adds a many2one field in the stock.picking model.
Features:
- Define carrier with image/logo
- Automatically create vendor (res.partner) record with same info
- Print custom shipping labels
    """,
    'depends': [
        'base',
        'sale',
        'stock',
        'delivery',
        'stock_delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/paperformat_data.xml',
        'views/delivery_carrier_views.xml',
        'views/stock_picking_views.xml',
        'report/delivery_label_report.xml',
        'report/delivery_label_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
