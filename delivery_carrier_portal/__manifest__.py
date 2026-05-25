# -*- coding: utf-8 -*-
{
    'name': 'Carrier Portal',
    'version': '18.0.2.0.0',
    'summary': 'Multi-carrier delivery portal with driver hierarchy, cash management & map tracking',
    'category': 'Sales/Sales',
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    'depends': ['sale_management', 'website', 'portal', 'stock'],
    'data': [
        'security/delivery_portal_groups.xml',
        'security/ir.model.access.csv',
        'views/delivery_carrier_company_views.xml',
        'views/carrier_pricing_views.xml',
        'views/delivery_driver_views.xml',
        'views/delivery_cash_remittance_views.xml',
        'views/sale_order_delivery_views.xml',
        'views/delivery_dashboard_views.xml',
        'views/delivery_portal_menus.xml',
        'report/delivery_trip_report.xml',
        'report/settlement_paper_format.xml',
        'report/settlement_report.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'delivery_carrier_portal/static/src/css/portal.css',
        ],
        'web.assets_backend': [
            'delivery_carrier_portal/static/src/css/dashboard.css',
        ],
    },
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
