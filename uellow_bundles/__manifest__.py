{
    'name': 'Uellow — Product Bundles',
    'version': '18.0.1.0.0',
    'summary': 'Bundles: sell several products as ONE product with one '
               'price — one cart line, one card, full component detail on '
               'the product page. Surfaced in the mobile app + builder.',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['website_sale', 'sale_management', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/bundle_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
