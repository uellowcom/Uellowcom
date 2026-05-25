# -*- coding: utf-8 -*-
{
    'name': 'Taly Payment Gateway - Buy Now Pay Later',
    'version': '18.0.2.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Taly BNPL Integration - اشتري الآن وادفع لاحقاً مع تالي',
    'description': """
Taly Payment Gateway Integration for Odoo 18
=============================================
* Accept payments via Taly (Buy Now Pay Later)
* Split in 3 or Pay Later options
* Full dashboard with statistics and reports
* On-Site Messaging widget on product pages
* Real-time webhook processing
* Full Arabic RTL support
* Refund management from Odoo backend
    """,
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'depends': ['payment', 'website_sale', 'account', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'security/payment_taly_security.xml',
        'data/payment_provider_data.xml',
        # ── Views (actions must be defined before menus that reference them) ──
        'views/payment_taly_provider_views.xml',
        'views/payment_taly_transaction_views.xml',
        'views/payment_taly_dashboard_views.xml',
        'views/payment_taly_log_views.xml',
        'report/payment_taly_report_views.xml',      # action_taly_report defined here
        'wizard/payment_taly_refund_wizard_views.xml',
        # ── Menus last (all actions must exist before this file) ──
        'views/payment_taly_menus.xml',
        # ── Website templates ──
        'views/payment_taly_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'payment_taly/static/src/css/taly_dashboard.css',
            'payment_taly/static/src/js/taly_dashboard.js',
        ],
        'website.assets_frontend': [
            'payment_taly/static/src/css/taly_frontend.css',
            'payment_taly/static/src/js/taly_product_widget.js',
        ],
    },
    'images': ['static/src/img/taly_logo.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
