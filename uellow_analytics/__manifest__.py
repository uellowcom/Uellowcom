{
    'name': 'Uellow AI Analytics',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Analytics dashboard for Beena AI performance and sales insights',
    'author': 'Uellow',
    'depends': ['web', 'sale_management', 'uellow_ai_engine'],
    'data': [
        'security/ir.model.access.csv',
        'views/analytics_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'uellow_analytics/static/src/xml/analytics_template.xml',
            'uellow_analytics/static/src/css/analytics.css',
            'uellow_analytics/static/src/js/analytics.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
