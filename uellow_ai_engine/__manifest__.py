{
    'name': 'Uellow AI Engine — Beena',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'AI Sales Assistant powered by Claude API',
    'author': 'Uellow',
    'depends': ['website', 'website_sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'views/ai_session_views.xml',
        'views/ai_settings_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_ai_engine/static/src/css/beena.css',
            'uellow_ai_engine/static/src/js/beena.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
