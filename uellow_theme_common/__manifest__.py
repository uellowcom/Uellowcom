# -*- coding: utf-8 -*-
# Uellow Theme Common — fork of Droggol Theme Common (theme_prime backend layer).
# Source: Droggol Infotech Private Limited (OPL-1) — forked 2026-05.
# All Droggol attribution preserved per OPL-1 in COPYRIGHT.
{
    'name': 'Uellow Theme Common',
    'description': 'Backend layer of the Uellow Theme — models, settings, snippet '
                   'helpers used by uellow_theme. Forked from Droggol Theme Common '
                   'to give Uellow full control over theme behaviour without losing '
                   'the original code lineage (license preserved).',
    'summary': 'Backend models + Styling menu for the Uellow Theme.',
    'category': 'Website',
    'version': '18.0.1.0.0',
    'depends': [
        'website_sale_comparison',
        'website_sale_wishlist',
        'website_sale_stock',
        'website_sale_stock_wishlist',
    ],

    'license': 'OPL-1',
    'author': 'Uellow',
    'company': 'Uellow',
    'maintainer': 'Uellow',
    'website': 'https://uellow.com/',

    'data': [
        'security/ir.model.access.csv',
        'deprecated/ir.model.access.csv',
        'views/templates.xml',

        # Backend
        'views/backend/menu_label.xml',
        'views/backend/website_menu.xml',
        'views/backend/product_label.xml',
        'views/backend/product_template.xml',
        'views/backend/product_attribute.xml',
        'views/backend/product_brand.xml',
        'views/backend/dr_website_content.xml',
        'views/backend/product_pricelist.xml',
        'views/backend/pwa_screenshots.xml',
        'views/backend/pwa_shortcuts.xml',
        'views/backend/res_config_settings.xml',
        'views/backend/dr_theme_config.xml',
        'views/backend/category_label.xml',
        'views/backend/product_category.xml',
        'views/backend/website.xml',
        'views/backend/search_report.xml',

        'data/search_report_cron.xml',

        # Snippets
        'views/snippets/s_mega_menu.xml',

        # Uellow additions
        'views/backend/styling_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'uellow_theme_common/static/src/js/hooks.js',
            'uellow_theme_common/static/src/js/theme_config/*.xml',
            'uellow_theme_common/static/src/js/product/**/*',
            'uellow_theme_common/static/src/js/product_template_attribute_line/**/*',
        ],
        'website.assets_editor': [
            'uellow_theme_common/static/src/js/theme_config/*.js',
            'uellow_theme_common/static/src/js/theme_config/*.scss',
            'uellow_theme_common/static/src/js/navbar/*',
        ],
        'web.assets_frontend': [
            'uellow_theme_common/static/src/js/notification/**/*',
            'uellow_theme_common/static/src/js/product/**/*',
            'uellow_theme_common/static/src/js/product_template_attribute_line/**/*',
        ],
    },
    'installable': True,
    'application': False,
}
