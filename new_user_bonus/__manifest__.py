# -*- coding: utf-8 -*-
{
    'name': 'New User Bonus Banner',
    'version': '18.0.1.0.0',
    'summary': 'New User Bonus snippet block for Odoo Website Builder',
    'author': 'Uellow',
    'category': 'Website',
    'depends': ['website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/snippets.xml',
    ],
    'assets': {
        'website.assets_wysiwyg': [
            'new_user_bonus/static/src/xml/snippet_options.xml',
        ],
        'web.assets_frontend': [
            'new_user_bonus/static/src/js/new_user_bonus.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
