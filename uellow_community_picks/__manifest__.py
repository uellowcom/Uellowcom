# -*- coding: utf-8 -*-
{
    # وحدة «اختيار المجتمع» — ترشيح الزوّار للمنتجات ليظهروا في بلوك الرئيسية
    'name': 'Uellow Community Picks',
    'summary': 'ترشيح الزوّار للمنتجات (اختيار المجتمع) + زر الترشيح في صفحة المنتج',
    'version': '1.0',
    'author': 'Uellow',
    'category': 'Website/eCommerce',
    'depends': ['website_sale', 'uellow_mobile_manager'],
    'data': [
        'security/ir.model.access.csv',
        'views/community_pick_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_community_picks/static/src/community_nominate.js',
            'uellow_community_picks/static/src/community_nominate.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
