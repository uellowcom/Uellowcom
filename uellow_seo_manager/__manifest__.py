# -*- coding: utf-8 -*-
{
    'name': 'Uellow SEO Manager',
    'version': '18.0.1.0.0',
    'category': 'Website/SEO',
    'summary': (
        'Production-grade SEO command center: site audit + auto-fix + AI '
        'meta generator + Schema.org library + SERP preview + bulk ops + '
        'ranking tracker + dashboard. Adds Product/Breadcrumb/Organization '
        'JSON-LD, auto-fills image alt text, validates titles & descriptions, '
        'flags duplicate/missing tags, and reports a per-page score.'
    ),
    'description': """
Uellow SEO Manager
==================

A comprehensive SEO automation module that complements uellow_seo_auto
with active monitoring, scoring, and bulk auto-fixing.

Features
--------
* **Site Audit**: crawls products, categories, pages, scores each by 30+ checks
* **Auto-Fix**: bulk-fills missing meta titles, descriptions, image alts
* **Schema.org library**: Product, BreadcrumbList, Organization, WebSite,
  LocalBusiness, AggregateRating, FAQ, VideoObject
* **AI generator**: writes meta titles/descriptions from product data via Claude
* **SERP Preview**: live preview of how the page appears in Google
* **Per-page panel**: override meta + schema per product/category
* **Dashboard**: site-wide health score + top 10 worst pages
* **Hreflang manager** (delegated to uellow_seo_auto)
""",
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    'depends': [
        'website', 'website_sale', 'product',
        'uellow_seo_auto', 'uellow_mobile_manager',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/seo_manager_data.xml',
        'wizard/seo_bulk_wizard_views.xml',
        'wizard/seo_audit_wizard_views.xml',
        'views/seo_manager_views.xml',
        'views/seo_phase_views.xml',
        'views/seo_config_inherit.xml',
        'views/seo_head_inject.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'uellow_seo_manager/static/src/css/dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
