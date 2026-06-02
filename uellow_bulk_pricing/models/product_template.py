"""Per-product overrides for bulk pricing."""
from odoo import api, fields, models


class ProductTemplateBulkPricing(models.Model):
    _inherit = 'product.template'

    bulk_pricing_excluded = fields.Boolean(
        string='Exclude from bulk pricing',
        help='If ON, this product never shows bulk-pricing tiers on the '
             'product page — even if pricelist tiers exist.')
    bulk_safety_margin_override = fields.Float(
        string='Bulk safety margin override (%)',
        default=0.0,
        help='Per-product override of the global safety margin. 0 = use '
             'global. Useful for clearance items (allow lower margin) or '
             'high-margin items (force higher floor).')
    bulk_pricing_loss_risk = fields.Boolean(
        string='At loss-risk under current tiers',
        compute='_compute_loss_risk',
        store=False,
        help='True if at least one bulk-pricing tier would breach the cost '
             'floor under current settings.')

    @api.depends('list_price')
    def _compute_loss_risk(self):
        Cfg = self.env['uellow.bulk.pricing.config'].sudo()
        Item = self.env['product.pricelist.item'].sudo()
        cfg = Cfg.get_config()
        for r in self:
            risk = False
            try:
                floor = Cfg.safety_floor_for(r)
                if floor > 0:
                    items = Item.search([
                        '|', ('product_tmpl_id', '=', r.id),
                             ('product_id.product_tmpl_id', '=', r.id),
                        ('min_quantity', '>', 1),
                    ], limit=10)
                    for it in items:
                        if (it.fixed_price or 0) and it.fixed_price < floor:
                            risk = True
                            break
            except Exception:
                pass
            r.bulk_pricing_loss_risk = risk
