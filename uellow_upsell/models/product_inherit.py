from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    enable_upsell = fields.Boolean('Enable Upsell', default=True)
    enable_crosssell = fields.Boolean('Enable Cross-sell', default=True)
    upsell_title_en = fields.Char('Upsell Title (EN)', default='You might also like')
    upsell_title_ar = fields.Char('Upsell Title (AR)', default='قد يعجبك أيضاً')
