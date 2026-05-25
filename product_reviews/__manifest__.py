{
    'name': 'Product Customer Reviews',
    'version': '18.0.6.0.0',
    'depends': ['rating', 'product', 'website_sale', 'portal'],
    'data': [
        'security/ir.model.access.xml',
        'views/product_review_views.xml',
        'views/product_review_portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'product_reviews/static/src/css/reviews.css',
            'product_reviews/static/src/js/reviews.js',
        ],
        'web.assets_backend': [
            'product_reviews/static/src/css/reviews.css',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
