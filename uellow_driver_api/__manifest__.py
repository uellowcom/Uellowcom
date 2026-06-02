# -*- coding: utf-8 -*-
{
    'name': 'Uellow Driver API',
    'version': '18.0.1.0.0',
    'summary': 'Mobile driver app backend — auth, orders, trips, cash, payment link',
    'description': """Backend endpoints powering the Uellow Driver Flutter app.
Mirrors every capability of /delivery-portal/* under /api/driver/v1/*.

Endpoints
=========
* auth/login, auth/logout, me, me/status
* orders (list + detail + pickup/decline/start/confirm/fail/return)
* orders/<id>/payment-link  (POST/GET status/share/cancel)
* trips (list + detail + reorder)
* cash (ready/submit/history)
* notifications (inbox + mark-read + push-token registration)
* help (faq + ops chat)
* app/languages
""",
    'category': 'Sales/Sales',
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    'depends': [
        'base', 'mail', 'sale_management', 'website', 'stock',
        'delivery_carrier_portal',
        'payment',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
