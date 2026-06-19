# -*- coding: utf-8 -*-
{
    'name': 'Uellow Documents (Invoice & Sales Order)',
    'version': '18.0.1.0.0',
    'summary': 'Premium bilingual Uellow-branded invoice & sales order / quotation PDFs',
    'category': 'Accounting/Sales',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['account', 'sale_management'],
    'data': [
        'views/res_config_settings_views.xml',
        'report/paperformat.xml',
        'report/invoice_document.xml',
        'report/sale_order_document.xml',
        'report/purchase_order_document.xml',
        'report/delivery_document.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
}
