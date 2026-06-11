{
    'name': 'Uellow Brain — Personalization & Merchandising Engine',
    'version': '18.0.0.1.0',
    'summary': 'Best Match ranking (cost/margin-driven), profit guardrails, '
               'diversity, interest lifecycle, BNPL, discount discipline, '
               'automated offers — with a giant KPI dashboard.',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['product', 'sale', 'stock', 'website_sale', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'data/brain_data.xml',
        'data/cron.xml',
        'views/brain_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'uellow_brain/static/src/css/brain_dashboard.css',
            'uellow_brain/static/src/js/brain_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
