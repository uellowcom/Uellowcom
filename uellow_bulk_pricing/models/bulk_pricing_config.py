"""Bulk Pricing Intelligence — singleton settings model.

Sits on top of Odoo's pricelist-based bulk pricing. Reads exclusions and
the safety floor here, then returns the list of tiers to anyone asking
(the mobile API, the website product page, etc.).
"""
import logging
from collections import OrderedDict

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BulkPricingConfig(models.Model):
    _name = 'uellow.bulk.pricing.config'
    _description = 'Uellow Bulk Pricing — settings'

    name = fields.Char(default='Bulk Pricing settings', required=True)

    # ─── Master switch ─────────────────────────────────────────
    enabled = fields.Boolean(
        string='Bulk pricing enabled',
        default=True,
        help='OFF = no product anywhere shows bulk-pricing tiers.')

    # ─── Display ───────────────────────────────────────────────
    max_tiers_shown = fields.Integer(
        string='Tiers shown per product',
        default=4,
        help='How many bulk-pricing tiers to display on the product page. '
             'Default 4. Range 1–5. The top N by min_quantity asc are shown.')
    show_to_guest = fields.Boolean(
        string='Show to guest visitors',
        default=True,
        help='If OFF, bulk pricing is only visible to logged-in users.')

    # ─── Cost-floor protection ─────────────────────────────────
    cost_floor_enabled = fields.Boolean(
        string='Protect against loss (cost floor)',
        default=True,
        help='When ON, a bulk tier price never drops below cost + safety '
             'margin. This is the killer feature — prevents accidental '
             'loss when a discount % is too aggressive vs. product cost.')
    safety_margin_pct = fields.Float(
        string='Safety margin above cost (%)',
        default=2.0,
        help='Minimum profit % above cost. Example: cost=8 KD, safety=2% '
             '→ floor=8.16 KD. Even if pricelist says 7.50, system returns 8.16.')
    cost_floor_behavior = fields.Selection(
        [('cap', 'Cap at floor (lower discount, still discounted)'),
         ('hide', 'Hide tier entirely (skip it)')],
        string='When pricelist tier would breach floor',
        default='cap',
        help='CAP: tier still shows but at a smaller discount.\n'
             'HIDE: tier disappears entirely from the product page.')

    # ─── Exclusions ────────────────────────────────────────────
    excluded_category_ids = fields.Many2many(
        'product.public.category',
        relation='uellow_bulk_pricing_excl_cat_rel',
        string='Excluded categories',
        help='Products in any of these categories never show bulk pricing.')
    excluded_product_ids = fields.Many2many(
        'product.template',
        relation='uellow_bulk_pricing_excl_prod_rel',
        string='Excluded products',
        help='Specific products to exclude.')
    excluded_brand_value_ids = fields.Many2many(
        'product.attribute.value',
        relation='uellow_bulk_pricing_excl_brand_rel',
        string='Excluded brands',
        domain=[('attribute_id.id', '=', 1)],
        help='Brand attribute values to exclude. Uses attribute id=1 (Brand).')

    # ─── Auto-generation ───────────────────────────────────────
    auto_generate_when_missing = fields.Boolean(
        string='Auto-generate tiers when missing',
        default=False,
        help='If a product has no bulk-pricing rules in its pricelist, '
             'generate 4 tiers from the default template below. The cost '
             'floor still applies, so loss-making products auto-cap.')
    default_tier_template = fields.Text(
        string='Default tier template',
        default='5,5\n10,10\n25,15\n50,20',
        help='One tier per line: "min_qty,save_pct". Used when '
             'auto-generate is ON and a product has no pricelist tiers.')

    # ─── Hints ─────────────────────────────────────────────────
    show_next_tier_hint = fields.Boolean(
        string='Show "add X more for next tier" hint',
        default=True,
        help='Mobile app shows a small banner under the tier ladder: '
             '"Add 2 more for 20% off!" — drives upsell.')

    # ─── Quantity selector — global max ────────────────────────
    default_max_qty = fields.Integer(
        string='Default max quantity per order',
        default=10,
        help='Default upper bound for the quantity selector on the product '
             'page. Categories and products can override. The selector '
             'always starts at 1 (original price) and lets the customer '
             'increment up to this number.')

    @api.model
    def get_config(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    # ───────────────────────────── core logic ─────────────────
    @api.model
    def is_excluded(self, product):
        """Return True if this product is excluded from bulk pricing."""
        cfg = self.get_config()
        if not cfg.enabled:
            return True
        if not product:
            return True
        # Per-product override flag
        if getattr(product, 'bulk_pricing_excluded', False):
            return True
        # Excluded product list
        if cfg.excluded_product_ids and product.id in cfg.excluded_product_ids.ids:
            return True
        # Excluded category — checks product.public_categ_ids ∩ exclusion list
        if cfg.excluded_category_ids and hasattr(product, 'public_categ_ids'):
            ex = set(cfg.excluded_category_ids.ids)
            if any(c.id in ex for c in product.public_categ_ids):
                return True
        # Excluded brand — checks the variant's attribute values
        if cfg.excluded_brand_value_ids:
            ex = set(cfg.excluded_brand_value_ids.ids)
            try:
                for line in product.attribute_line_ids:
                    for val in line.value_ids:
                        if val.id in ex:
                            return True
            except Exception:
                pass
        return False

    @api.model
    def max_qty_for(self, product):
        """Resolve the effective max quantity for a product.
        Priority: product override → first matching category override → global.
        0 anywhere means 'use parent'.
        """
        cfg = self.get_config()
        # Per-product
        try:
            v = int(getattr(product, 'bulk_max_qty', 0) or 0)
            if v > 0:
                return v
        except Exception:
            pass
        # First category with an override
        try:
            for cat in (product.public_categ_ids or []):
                v = int(getattr(cat, 'bulk_max_qty', 0) or 0)
                if v > 0:
                    return v
        except Exception:
            pass
        return max(1, int(cfg.default_max_qty or 10))

    @api.model
    def safety_floor_for(self, product):
        """Return the minimum price this product can be sold at (cost +
        configured safety margin). Returns 0 if no floor applies."""
        cfg = self.get_config()
        if not cfg.cost_floor_enabled:
            return 0.0
        try:
            variant = product.product_variant_ids[:1]
            cost = float(variant.standard_price or 0)
        except Exception:
            cost = 0.0
        if cost <= 0:
            return 0.0
        override = getattr(product, 'bulk_safety_margin_override', 0) or 0
        margin = float(override) if override > 0 else float(cfg.safety_margin_pct or 0)
        return cost * (1 + margin / 100.0)

    @api.model
    def build_tiers(self, product, pricelist_items=None, list_price=None,
                   currency_sym=None):
        """Return the final tier list for a product, applying:
        exclusions → cost floor → max-tier limit → auto-generate fallback.

        Args:
            product: a product.template recordset (single).
            pricelist_items: optional pre-fetched list of pricelist items.
                             If None, returns auto-generated tiers only.
            list_price: optional pre-fetched list price.
            currency_sym: optional pre-fetched currency symbol.

        Returns:
            list of dicts: [{min_qty, price, currency, save_pct, capped}, ...]
        """
        cfg = self.get_config()
        if self.is_excluded(product):
            return []

        list_p = float(list_price if list_price is not None
                       else (product.list_price or 0))
        if list_p <= 0:
            return []
        sym = currency_sym or (
            product.currency_id.symbol if product.currency_id else 'KD')

        floor = self.safety_floor_for(product)
        cap_mode = cfg.cost_floor_behavior == 'cap'

        tiers = []
        seen_qtys = set()

        # Build from pricelist items first
        for it in (pricelist_items or []):
            try:
                min_q = int(it['min_quantity'])
                price = float(it['price'])
            except (KeyError, ValueError, TypeError):
                continue
            if min_q <= 1 or min_q in seen_qtys:
                continue
            seen_qtys.add(min_q)

            capped = False
            if floor > 0 and price < floor:
                if cap_mode:
                    price = floor
                    capped = True
                else:
                    continue  # hide

            if price >= list_p:
                continue  # not actually a discount

            tiers.append(OrderedDict([
                ('min_qty', min_q),
                ('price', round(price, 3)),
                ('currency', sym),
                ('save_pct', int(round((1 - price / list_p) * 100))
                              if list_p > 0 else 0),
                ('capped', capped),
            ]))

        # Auto-generate from defaults if nothing came from the pricelist
        if not tiers and cfg.auto_generate_when_missing:
            for line in (cfg.default_tier_template or '').splitlines():
                parts = [x.strip() for x in line.split(',') if x.strip()]
                if len(parts) != 2:
                    continue
                try:
                    min_q = int(parts[0])
                    save_pct = float(parts[1])
                except ValueError:
                    continue
                if min_q <= 1 or min_q in seen_qtys:
                    continue
                seen_qtys.add(min_q)
                price = list_p * (1 - save_pct / 100.0)
                capped = False
                if floor > 0 and price < floor:
                    if cap_mode:
                        price = floor
                        capped = True
                    else:
                        continue
                if price >= list_p:
                    continue
                tiers.append(OrderedDict([
                    ('min_qty', min_q),
                    ('price', round(price, 3)),
                    ('currency', sym),
                    ('save_pct', int(round((1 - price / list_p) * 100))),
                    ('capped', capped),
                ]))

        # Sort ascending by min_qty, then keep top N
        tiers.sort(key=lambda t: t['min_qty'])
        cap = max(1, min(5, int(cfg.max_tiers_shown or 4)))
        return tiers[:cap]
