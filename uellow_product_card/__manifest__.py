# -*- coding: utf-8 -*-
{
    'name': 'Uellow Product Card',
    'version': '18.0.7.0.0',
    'summary': 'CSS reskin for Uellow Theme product cards + bilingual RTL/LTR',
    'category': 'Website',
    'author': 'Uellow',
    'depends': ['website_sale', 'theme_prime'],
    # NOTE: this depends on theme_prime today and will flip to 'uellow_theme'
    # as part of the staged migration documented in
    # /root/uellow_backups/MIGRATION_RUNBOOK.md (step 5).
    'data': [],
    'assets': {
        'web.assets_frontend': [
            'uellow_product_card/static/src/css/product_card.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
