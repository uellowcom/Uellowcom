{
    'name': 'Uellow Mobile API',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': '[DEPRECATED — use uellow_mobile_manager v2] REST API for Flutter app',
    'author': 'Uellow',
    'depends': [
        'website_sale', 'sale_management',
        'uellow_ai_engine', 'uellow_loyalty',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'views/mobile_api_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
