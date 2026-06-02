{
    'name': 'Uellow SEO Landing Pages',
    'version': '18.0.2.0.0',
    'category': 'Website/SEO',
    'summary': (
        'Author and publish SEO-optimised landing pages: title/H1/intro per '
        'language, FAQ schema, BreadcrumbList, ItemList JSON-LD, draft → '
        'review → published workflow, hreflang, dedicated sitemap.'
    ),
    'author': 'Uellow W.L.L',
    'website': 'https://uellow.com',
    'depends': ['website_sale', 'website', 'uellow_multivendor', 'uellow_seo_auto'],
    'data': [
        'security/ir.model.access.csv',
        'views/seo_pages_views.xml',
        'views/page_templates.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
