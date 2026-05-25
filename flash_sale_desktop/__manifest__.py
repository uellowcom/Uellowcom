# -*- coding: utf-8 -*-
{
    'name': 'Flash Sale Desktop',
    'version': '18.0.1.0.0',
    'summary': 'Flash Sale widget for Odoo Website with countdown timer',
    'description': """
        Flash Sale Desktop
        ==================
        A beautiful flash sale section for your Odoo website homepage.
        Features:
        - Live countdown timer (resets daily)
        - Swiper slider for products
        - RTL/LTR automatic support (Arabic/English)
        - Discount badge and percentage display
        - Responsive layout (mobile → desktop)
    """,
    'author': 'Uellow',
    'category': 'Website',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/flash_sale_snippet.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'flash_sale_desktop/static/src/css/flash_sale.css',
            'flash_sale_desktop/static/src/js/flash_sale.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
