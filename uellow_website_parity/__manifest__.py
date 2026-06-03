{
    'name': 'Uellow — Website Parity (Flash deals page)',
    'version': '18.0.1.0.0',
    'summary': 'Bring mobile-app surfaces to the website: /flash-deals page reads from the same mobile.flash.sale records as the app, so the admin manages one place and both stay in sync.',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['website_sale', 'uellow_mobile_manager'],
    'data': [
        'views/flash_deals_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}
