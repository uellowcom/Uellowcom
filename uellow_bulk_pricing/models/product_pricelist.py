"""Don't stack bulk/quantity pricing on already-discounted products.

`product.pricelist._compute_price_rule` is the single chokepoint every
price path goes through (sale order line `_compute_pricelist_item_id` /
`_get_pricelist_price`, the website cart, the mobile API cart, product
listings, …). It selects the pricelist rule whose `min_quantity` matches
the requested quantity, then computes the price.

When `exclude_discounted` is ON and a product already has a discount
(compare_list_price > list_price), we recompute that product at
quantity=1 so no `min_quantity > 1` tier is ever selected — the customer
keeps the normal unit price even when buying several. Any non-quantity
pricelist rule (a flat discount applicable at qty 1) still applies, so
only the wholesale/quantity benefit is removed.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _compute_price_rule(self, products, quantity, currency=None, uom=None,
                            date=False, compute_price=True, **kwargs):
        res = super()._compute_price_rule(
            products, quantity, currency=currency, uom=uom, date=date,
            compute_price=compute_price, **kwargs)
        # Only matters when buying more than one (where a quantity tier
        # could kick in). Single-unit fetches (listings, default display)
        # are untouched, so no overhead there.
        if not (quantity and quantity > 1 and products):
            return res
        try:
            Cfg = self.env['uellow.bulk.pricing.config'].sudo()
            cfg = Cfg.get_config()
            if not (cfg.enabled and cfg.exclude_discounted):
                return res
            for product in products:
                if not Cfg.product_has_discount(product):
                    continue
                # Re-price this product as if qty were 1 → quantity tiers
                # are skipped, normal unit price is kept.
                single = super()._compute_price_rule(
                    product, 1.0, currency=currency, uom=uom, date=date,
                    compute_price=compute_price, **kwargs)
                if product.id in single:
                    res[product.id] = single[product.id]
        except Exception:
            _logger.exception(
                "uellow_bulk_pricing: discounted-exclusion price override failed")
        return res
