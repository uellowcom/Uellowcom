# -*- coding: utf-8 -*-
{
    "name": "Yellow Mobile API",
    "version": "1.0.0",
    "category": "API/Mobile",
    "summary": "Mobile API endpoints for Yellow e-commerce platform",
    "description": """
        Yellow Mobile API Module
        ========================
        
        This module provides comprehensive REST API endpoints for mobile applications
        using Odoo models as the database backend:
        
        Features:
        ---------
        * Authentication (JWT, OAuth, Firebase)
        * Product Management via product.product
        * Order Processing via sale.order
        * User Profiles via res.partner
        * Wallet System
        * Notifications
        * Reviews & Ratings
        * Wishlist Management
        
        API Documentation available at /mobile/v1/docs
    """,
    "author": "Yellow Development Team",
    "website": "https://uellow.com",
    "depends": [
        "base",
        "contacts",
        "website",
        "sale",
        "product",
        "auth_signup",
        "website_sale",
        "stock",
        "payment",
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "views/mobile_api_views.xml",
    ],
    "external_dependencies": {},
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
