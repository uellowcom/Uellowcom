# -*- coding: utf-8 -*-
{
    'name': 'Uellow Category Page',
    'version': '1.0',
    'summary': 'World-class, data-driven category page (v3c design) with a setting for every block.',
    'description': """
Redesigns the storefront category page (/shop/category) on top of the REAL Odoo
product/category data: a compact category hero with the category image, a
subcategory image row, quick presets, an AI/search bar, a free-shipping unlock
bar (live threshold) and a live flash strip — every block toggleable per website
from Settings. Restyles the product cards to the v3c look.
""",
    'author': 'Uellow',
    'category': 'Website',
    'depends': ['website_sale', 'uellow_theme'],
    'data': [
        'views/compat.xml',
        'views/res_config_settings.xml',
        'views/product_public_category_views.xml',
        'views/shop_layout_inherit.xml',
        'views/card_inherit.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_category_page/static/src/scss/category_page.scss',
            'uellow_category_page/static/src/js/category_page.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
