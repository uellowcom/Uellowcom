from odoo import fields, models


class ProductTag(models.Model):
    _inherit = 'product.tag'

    free_shipping = fields.Boolean(
        string='Free shipping (any product with this tag)',
        help='Tag a product with this and it ships free.',
    )
