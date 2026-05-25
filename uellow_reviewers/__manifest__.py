{
    'name': 'Uellow Reviewers',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Human reviewer system with commissions for Uellow',
    'author': 'Uellow',
    'depends': ['website', 'website_sale', 'sale_management', 'uellow_ai_engine'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'views/reviewer_views.xml',
        'views/reviewer_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_reviewers/static/src/css/reviewers.css',
            'uellow_reviewers/static/src/js/reviewers.js',
            'uellow_reviewers/static/src/js/reviewers_portal.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
