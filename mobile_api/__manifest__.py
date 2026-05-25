# -*- coding: utf-8 -*-
{
    "name": "Uellow Mobile API",
    "version": "18.0.1.0.0",
    "category": "API/Mobile",
    "summary": "Mobile API endpoints and models for Uellow e-commerce platform",
    "description": """
        Uellow Mobile API Module
        ========================
        Provides REST API endpoints and data models for the Uellow Flutter mobile app:
        - Authentication (JWT, Firebase, Social Login)
        - Device Registration & Push Notifications
        - Wallet System
        - Wishlist Management
        - Product View History
    """,
    "author": "Uellow",
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
        "portal",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequences.xml",
        "views/mobile_api_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
