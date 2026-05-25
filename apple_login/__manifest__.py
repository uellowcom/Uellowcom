# -*- coding: utf-8 -*-
{
    'name': 'Sign in with Apple',
    'version': '18.0.1.0.0',
    'category': 'Website/Authentication',
    'summary': 'Allow users to login or register using Apple ID',
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'depends': ['web', 'auth_signup', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/apple_login_menus.xml',
        'views/login_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'apple_login/static/src/css/apple_login.css',
            'apple_login/static/src/js/apple_login.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
