# -*- coding: utf-8 -*-
{
    'name': 'Mobile FastAPI',
    'version': '1.0.0',
    'category': 'API',
    'summary': 'Mobile API implementation using FastAPI',
    'description': """
        Mobile API implementation using FastAPI
        ======================================
        
        This module provides mobile API endpoints using FastAPI integration.
        It includes authentication, products, home, wallet, and notifications endpoints.
    """,
    'author': 'Uellow',
    'website': 'https://www.uellow.com',
    'depends': [
        'base',
        'fastapi',
        'product',
        'sale',
        'website_sale',
        'auth_signup',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fastapi_endpoint.xml',
        'views/mobile_user_views.xml',
        'views/mobile_menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
