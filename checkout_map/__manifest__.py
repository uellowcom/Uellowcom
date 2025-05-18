{
    'name': 'Checkout Map',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Interactive map for selecting location during checkout',
    'description': """
        This module adds an interactive map to the website checkout page.
        It allows customers to select their location on a map during checkout.
        The selected location data (coordinates and address) is stored with the order.
    """,
    'depends': [
        'website_sale',
        'contacts',
        'base_geolocalize',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/checkout_map_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'checkout_map/static/src/js/checkout_map_component.js',
            'checkout_map/static/src/js/checkout_map_injector_owl.js',
            'checkout_map/static/src/js/map_location_owl.js',
            'checkout_map/static/src/xml/checkout_map_component.xml'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
