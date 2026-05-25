{
    'name': 'Uellow Abandoned Cart Recovery',
    'version': '18.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Recover abandoned carts via WhatsApp/SMS/email — 3-step sequence with optional discount',
    'author': 'Uellow W.L.L',
    'depends': ['website_sale', 'sale_management', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/abandoned_cart_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
