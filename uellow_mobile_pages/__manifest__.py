# -*- coding: utf-8 -*-
{
    'name': 'Uellow Mobile Pages — Drag & Drop Builder',
    'version': '18.0.1.0.0',
    'category': 'Website/Mobile',
    'summary': 'Visual drag-and-drop builder for mobile app pages, themes, and bottom nav bar',
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'depends': ['base', 'website', 'web', 'uellow_mobile_manager'],
    'data': [
        'security/ir.model.access.csv',
        'data/theme_presets.xml',
        'data/seed_pages.xml',
        'views/mobile_page_views.xml',
        'views/mobile_navbar_views.xml',
        'views/builder_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
