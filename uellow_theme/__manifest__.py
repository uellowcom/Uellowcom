# -*- coding: utf-8 -*-
# Uellow Theme — fork of "Theme Prime" by Droggol Infotech (OPL-1) — 2026-05.
# All original Droggol attribution preserved per OPL-1 in COPYRIGHT.
{
    'name': 'Uellow Theme',
    'description': 'Premium storefront theme used by Uellow. Forked from '
                   'Theme Prime so we can iterate freely on layout, branding, '
                   'product page, SEO and performance without losing the '
                   'original code lineage (license preserved in COPYRIGHT).',
    'summary': 'Premium storefront theme for Uellow — branded, fast, SEO-tuned.',
    'category': 'Theme/eCommerce',
    'version': '18.0.1.0.0',
    'depends': ['uellow_theme_common'],

    'license': 'OPL-1',
    'author': 'Uellow',
    'company': 'Uellow',
    'maintainer': 'Uellow',
    'website': 'https://uellow.com/',

    'images': [
        'static/description/prime_cover.png',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/theme.ir.attachment.csv',
        'views/theme_dashboard_settings_views.xml',

        'views/sidebar.xml',
        'views/templates.xml',
        # SEO + speed: handled by the standalone `uellow_seo` module so the
        # tags survive any theme switch. The old views/seo_and_speed.xml in
        # this folder is kept for reference but not loaded.
        'views/components.xml',
        'views/layout.xml',
        'views/shop_layout.xml',
        'views/product_detail_page.xml',
        'views/pages.xml',
        'views/snippets.xml',
        'views/svg_images.xml',

        # Headers / Footers
        'views/headers.xml',
        'views/preheaders.xml',
        'views/uellow_header.xml',      # Uellow Banggood-style header (style 9)
        'views/uellow_mobile_drawer.xml',# Premium hamburger off-canvas
        # 'views/uellow_product_page.xml' — disabled; revert to original product page
        'views/footers.xml',
        'views/uellow_footer.xml',      # Uellow Marketplace footer (style 9)

        # Snippets
        'views/snippets/dynamic_snippets.xml',
        'views/snippets/s_banner.xml',
        'views/snippets/s_blog.xml',
        'views/snippets/s_clients.xml',
        'views/snippets/s_coming_soon.xml',
        'views/snippets/s_countdown.xml',
        'views/snippets/s_cover.xml',
        'views/snippets/s_cta.xml',
        'views/snippets/s_gallery.xml',
        'views/snippets/s_heading.xml',
        'views/snippets/s_icon_block.xml',
        'views/snippets/s_info_block.xml',
        'views/snippets/s_pricing.xml',
        'views/snippets/s_shop_offer.xml',
        'views/snippets/s_stats.xml',
        'views/snippets/s_subscribe.xml',
        'views/snippets/s_team.xml',
        'views/snippets/s_testimonial.xml',

        # ─── Consolidated storefront layer ────────────────────────────
        # Pulled in from the legacy product_page_custom + uellow_product_card
        # modules so the theme is self-contained after the migration.
        'storefront/data/storefront_rating_access.xml',
        'storefront/views/storefront_product_template.xml',
        'storefront/views/storefront_res_config.xml',
        'storefront/views/storefront_website_sale.xml',
        # NB: storefront_product_card.xml is intentionally NOT loaded —
        # it inherits theme_prime.product_item_price which is a
        # theme.ir.ui.view (not ir.ui.view) and can't be inherited the
        # normal way. The legacy uellow_product_card module had
        # data: [] for the same reason. Only the CSS (asset bundle) ships.
    ],
    'assets': {
        'web.assets_frontend': [
            ('prepend', 'uellow_theme/static/src/js/website_sale_utils.js'),
            # Libraries
            'uellow_theme/static/lib/OwlCarousel2-2.3.4/assets/owl.carousel.css',
            'uellow_theme/static/lib/OwlCarousel2-2.3.4/assets/owl.theme.default.css',
            # Frontend
            'uellow_theme/static/src/js/website.js',
            'uellow_theme/static/src/js/website_sale.js',
            'uellow_theme/static/src/js/website_sale_wishlist.js',

            'uellow_theme/static/src/js/sidebar/**/*',
            'uellow_theme/static/src/js/dialog/**/*',
            'uellow_theme/static/src/js/pwa/pwa.js',
            'uellow_theme/static/src/js/suggested_product_slider/**/*',
            'uellow_theme/static/src/js/searchbar/**/*',

            'uellow_theme/static/src/js/core/mixins.js',
            'uellow_theme/static/src/js/frontend/comparison.js',
            'uellow_theme/static/src/js/frontend/bottombar.js',

            'uellow_theme/static/src/scss/theme.scss',
            'uellow_theme/static/src/scss/rtl.scss',
            'uellow_theme/static/src/scss/variants.scss',
            'uellow_theme/static/src/scss/website.scss',
            'uellow_theme/static/src/scss/website_sale.scss',
            'uellow_theme/static/src/scss/sliders.scss',
            'uellow_theme/static/src/scss/icon-packs/website.scss',
            'uellow_theme/static/src/scss/utils.scss',
            'uellow_theme/static/src/scss/snippets/cards.scss',
            'uellow_theme/static/src/scss/front_end/dynamic_snippets.scss',
            'uellow_theme/static/src/scss/front_end/category_filters.scss',
            'uellow_theme/static/src/scss/front_end/image_hotspot.scss',
            'uellow_theme/static/src/scss/snippets/2_col_deal.scss',
            'uellow_theme/static/src/scss/snippets/image_products.scss',
            'uellow_theme/static/src/scss/front_end/bottom_bar.scss',
            'uellow_theme/static/src/scss/uellow_header.scss',  # Banggood-style header (style 9)
            'uellow_theme/static/src/scss/uellow_footer.scss',  # Uellow marketplace footer (style 9)
            'uellow_theme/static/src/scss/uellow_mobile_drawer.scss',  # Mobile hamburger drawer
            # 'uellow_theme/static/src/scss/uellow_product_page.scss' — disabled; revert
            'uellow_theme/static/src/js/frontend/uc_header.js', # Beena AI button wiring
            'uellow_theme/static/src/snippets/s_blog_posts/000.scss',
            # Core
            'uellow_theme/static/src/js/core/snippet_root_widget.js',
            'uellow_theme/static/src/xml/core/snippet_root_widget.xml',

            'uellow_theme/static/src/js/core/product_root_widget.js',

            'uellow_theme/static/src/js/core/cart_manager.js',
            'uellow_theme/static/src/components/notification/notification.xml',

            # Snippets
            'uellow_theme/static/src/snippets/s_tp_countdown/000.xml',
            'uellow_theme/static/src/js/frontend/dynamic_snippets.js',
            'uellow_theme/static/src/xml/frontend/dynamic_snippets.xml',
            'uellow_theme/static/src/xml/cards.xml',
            'uellow_theme/static/src/xml/listing_cards.xml',
            'uellow_theme/static/src/xml/frontend/utils.xml',
            'uellow_theme/static/src/xml/frontend/category_filters.xml',
            'uellow_theme/static/src/xml/frontend/2_col_deal.xml',
            'uellow_theme/static/src/xml/frontend/s_image_products.xml',
            'uellow_theme/static/src/xml/frontend/s_product_grid.xml',
            'uellow_theme/static/src/xml/frontend/hierarchical_category_templates.xml',
            'uellow_theme/static/src/xml/frontend/s_category.xml',
            'uellow_theme/static/src/xml/frontend/brands.xml',
            'uellow_theme/static/src/xml/frontend/image_hotspot.xml',   # TODO: kishan
            'uellow_theme/static/src/xml/website_sale.xml',

            # ─── Storefront assets (from product_page_custom + uellow_product_card) ─
            'uellow_theme/static/src/css/storefront/product_page.css',
            'uellow_theme/static/src/css/storefront/desc_tab.css',
            'uellow_theme/static/src/css/storefront/product_card.css',
            'uellow_theme/static/src/js/storefront/product_page.js',
            'uellow_theme/static/src/js/storefront/desc_tab.js',
        ],
        'web._assets_primary_variables': [
            'uellow_theme/static/src/scss/primary_variables.scss',
            'uellow_theme/static/src/scss/mixins.scss',
        ],
        'web._assets_frontend_helpers': [
            'uellow_theme/static/src/scss/bootstrap_overridden.scss',
        ],
        'website.assets_wysiwyg': [
            'uellow_theme_common/static/src/js/hooks.js',
            'uellow_theme/static/src/js/editor/snippets.editor.js',
            'uellow_theme/static/src/scss/editor/editor.scss',

            # 'uellow_theme/static/src/scss/editor/dialogs/dialog_snippet_configurator.scss',
            'uellow_theme/static/src/xml/editor/dialogs/snippet_configurator_dialog.xml',
            'uellow_theme/static/src/xml/frontend/image_hotspot.xml',

            'uellow_theme/static/src/js/editor/snippets/snippets.options.js',
            'uellow_theme/static/src/xml/frontend/documents.xml',
            'uellow_theme/static/src/components/*'
        ],
        'web_editor.wysiwyg_iframe_editor_assets': [
            'uellow_theme/static/src/scss/wysiwyg_snippets.scss',
        ],
        'web_editor.assets_wysiwyg': [
            'uellow_theme/static/src/scss/wysiwyg_snippets.scss',
        ],
        'web.assets_backend': [
            # Backend CSS bundled by storefront layer
            'uellow_theme/static/src/css/storefront/desc_tab_backend.css',
        ],
    },
}
