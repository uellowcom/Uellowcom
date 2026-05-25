{
    'name': 'Uellow Smart Fit Engine',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'AI-powered size recommendation and body profile for Uellow',
    'author': 'Uellow',
    'depends': ['website', 'website_sale', 'uellow_ai_engine'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'views/fit_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_smart_fit/static/src/css/smart_fit.css',
            'uellow_smart_fit/static/src/js/smart_fit.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
