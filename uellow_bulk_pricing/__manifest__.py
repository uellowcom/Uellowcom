{
    'name': 'Uellow Bulk Pricing Intelligence',
    'version': '18.0.1.0.0',
    'category': 'Sales/Pricing',
    'summary': 'Smart bulk-pricing: exclusions, cost-floor protection, auto-tiers',
    'description': """
Uellow Bulk Pricing Intelligence
================================
Sits on top of Odoo's standard pricelist bulk-pricing. Adds:

* Cost-floor protection — a tier price NEVER drops below cost +
  configurable safety margin. Either CAP at the floor or HIDE the tier.
* Exclusions — by category, product, or brand.
* Per-product override — exclude a single product OR set a custom
  safety-margin floor for that one product.
* Tier limit — show top N tiers (default 4) on product page.
* Show-to-guest toggle — bulk pricing only for logged-in users.
* Auto-generated tiers — if a product has no pricelist tiers, generate
  4 sensible defaults (configurable).
* Health page — products at risk of negative margin highlighted.
""",
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'depends': ['product', 'sale', 'website_sale', 'uellow_mobile_manager'],
    'data': [
        'security/ir.model.access.csv',
        'data/default_config.xml',
        'views/bulk_pricing_settings_views.xml',
        'views/product_template_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
