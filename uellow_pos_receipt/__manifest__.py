# -*- coding: utf-8 -*-
{
    'name': 'Uellow POS Receipt',
    'version': '18.0.1.0.6',
    'category': 'Point of Sale',
    'summary': 'Custom bilingual AR/EN POS receipt for Uellow',
    'author': 'Uellow W.L.L',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'uellow_pos_receipt/static/src/css/receipt.css',
            'uellow_pos_receipt/static/src/xml/uellow_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
}
