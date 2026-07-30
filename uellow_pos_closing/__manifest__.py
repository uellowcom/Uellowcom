{
    'name': 'Uellow POS Closing Report',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Professional cashier closing (Z) report — A4 + 80mm POS receipt',
    'description': """
Cashier daily closing / Z-report for the POS backend session, in two print
formats:
  * A4  — full professional page (payments, cash reconciliation, sales
          summary, top products, signatures).
  * 80mm — POS thermal-receipt layout with the same closing details.
Both are bilingual (EN + AR) and available from the session's Print menu
and dedicated header buttons.
""",
    'author': 'Uellow',
    'license': 'LGPL-3',
    'depends': ['point_of_sale'],
    'data': [
        'report/pos_closing_reports.xml',
        'report/pos_closing_templates_a4.xml',
        'report/pos_closing_templates_receipt.xml',
        'views/pos_session_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'uellow_pos_closing/static/src/js/closing_receipt_button.js',
            'uellow_pos_closing/static/src/xml/closing_popup.xml',
        ],
    },
    'installable': True,
    'application': False,
}
