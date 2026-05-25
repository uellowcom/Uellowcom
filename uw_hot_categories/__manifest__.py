# -*- coding: utf-8 -*-
{
    'name': 'UW Hot Categories Block',
    'version': '18.0.1.0.0',
    'summary': 'Hot Categories snippet block for Odoo 18 website builder',
    'description': '''
Fully customizable Hot Categories block for Odoo 18 website builder.
Features:
- Select main + 6 sub categories by ID
- Full color control (per block, per sub-category)
- RTL/LTR auto-detection
- Responsive (mobile hides large card)
- Available in Website > Snippets panel
    ''',
    'category': 'Website/Snippets',
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/snippets.xml',
        'views/snippet_options.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uw_hot_categories/static/src/css/hot_cats.css',
            'uw_hot_categories/static/src/js/hot_cats.js',
        ],
        'website.assets_wysiwyg': [
            'uw_hot_categories/static/src/js/hot_cats_options.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
