{
    'name': 'Uellow — Shipping Pro (zones · windows · cash surcharge · cities DB)',
    'version': '18.0.1.0.0',
    'summary': 'Layered on delivery_carrier_portal: bilingual cities + delivery zones (normal/remote/far) + per-payment cash surcharge + time-of-day availability windows',
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': [
        'delivery_carrier_portal',
        'uellow_mobile_pages',
        'website_sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_zone_views.xml',
        'views/delivery_city_views.xml',
        'views/carrier_pricing_rule_views.xml',
        'views/delivery_carrier_company_views.xml',
        'data/kuwait_zones_seed.xml',
        'data/kuwait_cities_seed.xml',
        'data/carrier_seed.xml',
    ],
    'installable': True,
    'application': False,
}
