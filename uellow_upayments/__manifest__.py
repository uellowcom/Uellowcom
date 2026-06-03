{
    'name': 'Uellow — UPayments Gateway',
    'version': '18.0.1.0.0',
    'summary': 'Direct UPayments charge (payment link) + return/webhook for the mobile checkout. Bypasses the website-cart redirect.',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['sale', 'payment'],
    'data': [
        'data/params.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
}
