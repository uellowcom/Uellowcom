from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    dynamic_price = fields.Float('Dynamic Price', default=0.0)
    dynamic_rule_id = fields.Many2one(
        'uellow.dynamic.pricing.rule', string='Active Dynamic Rule',
        ondelete='set null',
    )
    dynamic_pricing_enabled = fields.Boolean('Enable Dynamic Pricing', default=True)

    def get_effective_price(self):
        """Return dynamic price if set and rule is active, else list_price."""
        self.ensure_one()
        if (self.dynamic_pricing_enabled and
                self.dynamic_price > 0 and
                self.dynamic_rule_id and
                self.dynamic_rule_id.active):
            return self.dynamic_price
        return self.list_price
