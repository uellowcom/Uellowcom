# -*- coding: utf-8 -*-
{
    'name': 'Uellow SEO & Speed',
    'summary': 'Open Graph, Twitter Card, Product JSON-LD, canonical URLs '
               'and lazy-loading hints — theme-agnostic.',
    'description': (
        "Storefront SEO and speed essentials, packaged independent of the "
        "active theme so they keep working across theme switches:\n"
        "\n"
        "  • Open Graph (og:title / og:image / og:url / og:site_name)\n"
        "  • Twitter Card (summary_large_image)\n"
        "  • Schema.org/Product JSON-LD on product detail pages\n"
        "    (eligible for Google rich snippets — price, stock, brand)\n"
        "  • Canonical URL on every page (kills facet-URL duplicates)\n"
        "  • preconnect + dns-prefetch to Google Fonts\n"
        "  • loading='lazy' + decoding='async' on below-the-fold images\n"
        "  • Theme-color meta (Chrome address bar tint, PWA splash)\n"
        "\n"
        "Depends only on `website` + `website_sale` so it survives any "
        "theme module being installed, swapped or upgraded."
    ),
    'category': 'Website/SEO',
    'version': '18.0.1.0.0',
    'author': 'Uellow',
    'website': 'https://uellow.com/',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/seo_meta.xml',
        'views/product_jsonld.xml',
        'views/lazy_images.xml',
        'views/product_seo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
