{
    'name': 'Uellow Loyalty Points',
    'version': '18.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Customer loyalty points — earn on purchase/review/referral, tiers, redeem as discount',
    'author': 'Uellow W.L.L',
    'depends': ['website_sale', 'sale_management', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/loyalty_views.xml',
        'views/menus.xml',
        'views/portal_loyalty.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
