# -*- coding: utf-8 -*-
{
    "name": "Uellow Mobile API",
    "version": "18.0.1.0.0",
    "category": "API/Mobile",
    "summary": "[DEPRECATED — use uellow_mobile_manager v2] Mobile API for Uellow",
    "description": """
        DEPRECATED 2026-05-30
        =====================
        Superseded by /api/mobile/v2/* in `uellow_mobile_manager`.
        See DEPRECATED.md for the migration plan + endpoint map.
        Sunset target: 2026-10-01.
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
