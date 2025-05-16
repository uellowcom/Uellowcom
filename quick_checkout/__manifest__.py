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
    ],
    'assets': {
        'web.assets_frontend': [
            'quick_checkout/static/src/js/quick_checkout.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
