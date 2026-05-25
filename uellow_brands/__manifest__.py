{
    'name': 'Uellow Brands Slider',
    'version': '18.0.1.0.0',
    'summary': 'Brands slider snippet for website with dynamic data from Odoo',
    'category': 'Website',
    'author': 'Uellow',
    'depends': ['website', 'website_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_brands/static/src/css/brands_slider.css',
            'uellow_brands/static/src/js/brands_slider.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
