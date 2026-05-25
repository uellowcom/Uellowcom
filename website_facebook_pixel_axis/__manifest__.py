# -*- coding: utf-8 -*-
{
    'name': 'Facebook Pixel in odoo, Facebook Pixel integration in odoo',
    'version': '18.0.0.1',
    'category': 'Website',
    'license': 'OPL-1',
    'summary': """
        Odoo facebook pixel integration for odoo website product and Facebook Pixel Analytics for track event of odoo website, Pages, add to cart, wishlist, Track page views for odoo ecommerce website.
    """,
    'description': ' Odoo facebook pixel integration for odoo website product and FB Pixel for track event of odoo website.',
    'images': ['static/description/banner.png'],
    'depends': [
        'website'
    ],
    'data': [
        'views/website_config_settings.xml',
        'views/website_templates.xml',
    ],
    'price': 15.0,
    'currency': 'USD',
    'support': 'business@axistechnolabs.com',
    'author': 'Axis Technolabs',
    'website': 'http://www.axistechnolabs.com',
    'application': False,
    'installable': True,
    'auto_install': False,
}
