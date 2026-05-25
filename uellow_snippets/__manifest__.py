{
    'name': 'New Arrival Snippet',
    'version': '18.0.1.0',
    'summary': 'New Arrivals Snippet for Uellow Website Builder',
    'depends': ['website', 'website_sale'],
    'author': 'Uellow',
    'license': 'LGPL-3',
    'data': [
        'views/snippets.xml',
        'views/snippet_options.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'uellow_snippets/static/src/js/new_arrivals.js',
            'uellow_snippets/static/src/css/new_arrivals.css',
        ],
    },
    'installable': True,
    'auto_install': False,
}
