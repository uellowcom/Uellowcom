{
    'name': 'Fast Buy',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Fast Buy - Quick order dialog',
    'depends': ['website_sale', 'contacts', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/fast_buy_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
