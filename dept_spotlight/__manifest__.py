# -*- coding: utf-8 -*-
{
    'name': 'Department Spotlight Banner',
    'version': '18.0.1.0.0',
    'summary': 'Professional category/department showcase snippet for Odoo Website Builder',
    'author': 'Uellow',
    'category': 'Website',
    'depends': ['website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/snippets.xml',
    ],
    'assets': {
        'website.assets_wysiwyg': [
            'dept_spotlight/static/src/xml/snippet_options.xml',
        ],
        'web.assets_frontend': [
            'dept_spotlight/static/src/js/dept_spotlight.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
