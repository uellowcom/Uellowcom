{
    'name': 'Quick Checkout',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Quick checkout form to collect client name and phone',
    'description': """
        This module adds a quick checkout form to the website checkout page.
        It allows customers to quickly place an order by providing just their name and phone number.
        When submitted, it clears the cart and creates a contact and sale order.
    """,
    'depends': [
        'website_sale',
        'theme_prime',
        'contacts',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/quick_checkout_templates.xml',
        'views/sale_order_views.xml',
        'views/checkout_map_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'quick_checkout/static/src/js/quick_checkout.js',
            'quick_checkout/static/src/js/checkout_map_component.js',
            'quick_checkout/static/src/js/checkout_map_injector_owl.js',
            'quick_checkout/static/src/js/map_location.js',
            'quick_checkout/static/src/js/checkout_map_injector.js',
            'quick_checkout/static/src/xml/quick_checkout_templates.xml',
            'quick_checkout/static/src/xml/checkout_map_component.xml',
            'quick_checkout/static/src/xml/map_location_templates.xml'
        ],
        'web.assets_frontend_lazy': [
            'quick_checkout/static/src/js/theme_prime_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
