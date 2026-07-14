{
    'name': 'Uellow SEO Automation',
    'version': '18.0.2.0.0',
    'category': 'Website/SEO',
    'summary': (
        'Production-grade SEO: per-product meta + JSON-LD, hreflang, sitemap, '
        'robots.txt, Search Console verification, BreadcrumbList + '
        'Organization + WebSite schema, AI bulk generation wizard.'
    ),
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    # `uellow_multivendor` provides the menu parent we attach to; without it
    # the install crashes on `parent="uellow_multivendor.menu_marketplace_main"`.
    'depends': ['website_sale', 'product', 'uellow_multivendor'],
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/seo_config_data.xml',
        'wizard/seo_generate_wizard_views.xml',
        'views/seo_views.xml',
        'views/seo_head_inherit.xml',
        'views/hreflang_country_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
