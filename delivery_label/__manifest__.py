# -*- coding: utf-8 -*-
{
    'name': 'Delivery Label',
    'version': '18.0.1.3.0',
    'category': 'Inventory/Delivery',
    'summary': 'Custom delivery labels for Odoo 18 sales and inventory flows',
    'description': """
Delivery Label Module
====================
This module extends delivery carriers and stock pickings with custom label printing.
Features:
- Configure carrier logos and vendor details
- Automatically create and synchronize a vendor contact
- Print custom shipping labels from delivery orders
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
