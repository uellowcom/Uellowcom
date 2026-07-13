{
    'name': 'Uellow Dropship',
    'version': '18.0.0.1.0',
    'category': 'Website',
    'summary': 'Provider-agnostic dropshipping engine (AliExpress, CJ, Spocket, ...) with display-dont-store catalog',
    'description': """
Uellow Dropship
===============
Provider-agnostic dropshipping for Uellow.

Design principles
-----------------
* Display don't store: millions of source listings live in a lightweight
  ``dropship.product`` table. A real ``product.template`` is materialized ONLY
  at order time (idempotent by provider+source_id) so the DB grows by orders,
  not by listings.
* Provider-agnostic: every provider is an adapter implementing the standard
  ``DropshipAdapter`` interface. Add AliExpress / CJ / Spocket without touching
  the core.
* Isolation: dropship products are flagged ``is_dropship=True``, ``type=consu``
  (no stock), ``default_code=DS-*`` and served on their own website(s). They
  never mix with the live Uellow catalog.
""",
    'author': 'Uellow',
    'depends': ['base', 'product', 'website_sale', 'sale_management', 'uellow_ai_engine', 'uellow_mobile_manager', 'uellow_mobile_pages'],
    'data': [
        'security/ir.model.access.csv',
        'data/dropship_data.xml',
        'data/dropship_cron.xml',
        'views/dropship_provider_views.xml',
        'views/dropship_product_views.xml',
        'views/dropship_category_views.xml',
        'views/dropship_text_rule_views.xml',
        'views/dropship_dashboard_views.xml',
        'views/dropship_report.xml',
        'views/dropship_import_views.xml',
        'views/dropship_browse_views.xml',
        'views/dropship_price_intel_views.xml',
        'views/dropship_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/dropship_settings_views.xml',
        'views/storefront_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
