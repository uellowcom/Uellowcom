{
    'name': 'Uellow Ops UX — PO receipt/payment badges + newest-first lists',
    'version': '18.0.1.0.0',
    'summary': 'Colored receipt & payment status on purchase orders; operational lists sorted newest-first',
    'category': 'Inventory/Purchase',
    'author': 'Uellow',
    'depends': ['purchase', 'purchase_stock', 'stock'],
    'data': [
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
