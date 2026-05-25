# -*- coding: utf-8 -*-
{
    'name': 'Uellow - You May Like Block',
    'version': '18.0.1.0.0',
    'summary': 'Adds a "You May Like" product block to the website builder blocks list.',
    'description': """
        Uellow You May Like
        ===================
        A dynamic product recommendation block for your Odoo website.
        
        Features:
        - Registers as a building block in the website editor (s_uellow_you_may_like)
        - Auto-loads products via lazy scroll (3 rounds auto, then manual button)
        - Fully RTL/LTR aware (Arabic & English)
        - Displays discount %, old price, star rating, stock status
        - Vertical sliding micro-text (save / delivery / quality)
        - Express + Taly payment badges
        - Responsive: 2-col mobile → 5-col desktop
        - Zero external dependencies (pure vanilla JS + Font Awesome already in Odoo)
    """,
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'category': 'Website',
    'license': 'LGPL-3',

    'depends': ['website_sale'],

    'data': [
        'views/snippets.xml',
        'views/assets.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'uellow_you_may_like/static/src/css/uellow_yml.css',
            'uellow_you_may_like/static/src/js/uellow_yml.js',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
