{
    'name': 'Uellow Fraud Detection',
    'version': '18.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Detect suspicious COD orders — repeated cancellations, same address multiple names, auto-flag and block',
    'author': 'Uellow W.L.L',
    'depends': ['website_sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/fraud_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
