from odoo import fields, models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    free_shipping = fields.Boolean(
        string='Free shipping (all products in this category)',
        help='Marks every product whose public_categ_ids contains this '
             'category (or any descendant) as free-shipping.',
    )
