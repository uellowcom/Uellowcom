# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description_ar = fields.Html(
        string="وصف المنتج (عربي)",
        translate=False,
        sanitize=True,
        sanitize_overridable=True,
        help="وصف تفصيلي للمنتج باللغة العربية — يظهر في تاب 'الوصف' بصفحة المنتج",
    )

    website_description_en = fields.Html(
        string="Product Description (English)",
        translate=False,
        sanitize=True,
        sanitize_overridable=True,
        help="Detailed product description in English — shown in the Description tab on the product page",
    )
