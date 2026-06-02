{
    'name': 'Product Page Custom',
    'version': '18.0.2.2.1',
    'summary': 'Custom Product Page — WhatsApp, Swatches, Installment, Discount, Related Products, Bilingual Description',
    'category': 'Website/eCommerce',
    'author': 'Custom',
    'depends': ['website_sale', 'theme_prime'],
    # NOTE: this depends on theme_prime today and will flip to 'uellow_theme'
    # as part of the staged migration documented in
    # /root/uellow_backups/MIGRATION_RUNBOOK.md (step 5).
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'views/website_sale_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'product_page_custom/static/src/css/product_page.css',
            'product_page_custom/static/src/css/desc_tab.css',
            'product_page_custom/static/src/js/product_page.js',
            'product_page_custom/static/src/js/desc_tab.js',
        ],
        'web.assets_backend': [
            'product_page_custom/static/src/css/desc_tab_backend.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
