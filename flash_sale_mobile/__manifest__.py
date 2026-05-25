# -*- coding: utf-8 -*-
# ============================================================
# Flash Sale Mobile — Odoo 18 Enterprise
# ✅ xpath الصحيح لـ Odoo 18:
#    خطوة 1: snippet_groups  |  خطوة 2: snippet_structure
# ============================================================
{
    'name': 'Flash Sale Mobile',
    'version': '18.0.1.0.0',
    'summary': 'Flash Sale Mobile widget block for Odoo Website Builder',
    'category': 'Website',
    'author': 'Uellow',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/snippets.xml',
    ],
    'assets': {
        'website.assets_wysiwyg': [
            'flash_sale_mobile/static/src/snippets/s_flash_sale_v49/options.js',
        ],
        'web.assets_frontend': [
            'flash_sale_mobile/static/src/snippets/s_flash_sale_v49/flash_sale_v49.css',
            'flash_sale_mobile/static/src/snippets/s_flash_sale_v49/flash_sale_v49.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
