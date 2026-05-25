# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt. Ltd.
#    Website: http://www.devintellecs.com
#
#    For Module Support: devintelle@gmail.com | Skype: devintelle
#
##############################################################################

{
    'name': 'Facebook Catalog | Facebook Shop Integration',
    'version': '18.0.1.0',
    'sequence': 1,
    'category': 'Generic Modules/Tools',
    'description': """
Facebook Shop Integration Odoo app allows you to connect your Odoo system with Facebook Shop and manage your product catalog from one place. With this app, you can export products directly from Odoo to Facebook, update product details, and ensure that your catalog always stays up to date. Automatic feed generation makes it easy to keep your Facebook Shop synchronized without extra effort.

The app also supports Facebook-specific product fields, so you can add or edit details required by Facebook directly in Odoo. It allows you to map both Facebook and Google product categories, ensuring correct categorization for better visibility and reach. Feeds can be generated in CSV, XML, or TSV formats, making them fully compatible with Facebook Catalog.

By managing everything from Odoo, you save time, reduce manual work, and make sure your customers always see the latest products in your Facebook Shop.
    """,
    'summary': 'Facebook catalog facebook shop facebook marketing facebook poriducts facebook catalog integration add products to facebook product feed live stock update Facebook Catalogue Facebook Shop integration Odoo products with Facebook Shop Facebook catalog connector Export Odoo products to Facebook Facebook product feed generator Facebook and Google categories Manage Facebook Shop Facebook Shop synchronization Facebook catalog management',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/facebook_product_data_feed.xml',
        'views/product_view.xml',
        'wizard/facebook_google_category_view.xml',
        'views/custom_facebook_category.xml',
        'views/custom_google_category.xml',
        # 'views/shop_fields.xml',  # Uncomment if needed
    ],
    'demo': [
        'demo/demo_data_feed_fields.xml',
    ],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    #author and support Details
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'https://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':25.0,
    'currency':'EUR',
    #'live_test_url':'https://youtu.be/A5kEBboAh_k',
}
