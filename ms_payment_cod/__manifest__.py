{
    "name": "Website Payment Cash on Delivery (COD)",
    "summary": """
        Cash on delivery payment method on the portal website
    """,
    "description": """
    """,
    "author": "Miftahussalam",
    "website": "https://blog.miftahussalam.com/",
    "category": "Accounting/Payment Providers",
    "version": "18.0.1.0.0",
    "depends": [
        "base",
        "product",
        "account",
        "payment",
        "payment_custom",
        "website_sale",
        "product",
    ],
    "data": [
        "data/account_payment_method.xml",
        "data/payment_method_data.xml",
        "data/payment_provider_data.xml",
        "data/product_product.xml",
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/payment_provider_views.xml",
        "views/templates.xml",
        "views/payment_form_templates.xml",
        "views/payment_transaction_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "ms_payment_cod/static/src/js/payment_form.js",
        ],
    },
    "demo": [

    ],
    "images": [
        "static/description/images/main_screenshot.png",
    ],
    "license": "OPL-1",
    "price": 15,
    "currency": "USD",
    "live_test_url": "https://odoo18.miftahussalam.com/",
}
