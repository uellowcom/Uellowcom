{
    'name': 'Uellow — Free Shipping Tagger',
    'version': '18.0.1.0.0',
    'summary': 'Mark products / categories / tags as eligible for free shipping; surfaces on the mobile app + website',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['product', 'website_sale', 'uellow_mobile_pages'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_category_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
