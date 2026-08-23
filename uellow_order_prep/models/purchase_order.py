# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # thumbnail shown next to the product in the PO / RFQ order-line list —
    # mirrors the sale.order.line image (uc_product_image).
    uc_product_image = fields.Binary(
        related='product_id.image_128', string='Image', store=False)
