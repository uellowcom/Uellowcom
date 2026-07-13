# -*- coding: utf-8 -*-
"""Uellow World shipping carrier.

Uellow World products ship INTERNATIONALLY from China — there is no local Kuwait
courier in the loop, so the local ``delivery.carrier`` records (each scoped to a
KW website/company) never apply to the World website (id 19 / company 7). With
no carrier the checkout showed NO shipping method at all and fell back to a
synthetic id that could not be selected/persisted.

This adds a dedicated delivery type whose rate is driven ENTIRELY by the Uellow
World settings (free by default, optional flat fee, optional free-over
threshold), so the admin controls World shipping from inside the module — no
per-zone courier config needed. ``_ensure_world_carrier`` creates the single
scoped carrier record idempotently.
"""
from odoo import api, fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('uellow_world', 'Uellow World (International)')],
        ondelete={'uellow_world': 'set default'})

    # ------------------------------------------------------------------ #
    # rating — read straight from the Uellow World settings
    # ------------------------------------------------------------------ #
    def uellow_world_rate_shipment(self, order):
        ICP = self.env['ir.config_parameter'].sudo()

        def _b(key, dflt='True'):
            return ICP.get_param(key, dflt) in ('True', '1', 'true')

        def _f(key, dflt=0.0):
            try:
                return float(ICP.get_param(key, dflt) or dflt)
            except (TypeError, ValueError):
                return dflt

        free = _b('uellow_dropship.free_shipping', 'True')
        flat = _f('uellow_dropship.shipping_price', 0.0)
        threshold = _f('uellow_dropship.free_ship_threshold', 0.0)
        amount = order.amount_untaxed if order else 0.0
        if free or flat <= 0.0 or (threshold and amount >= threshold):
            price = 0.0
        else:
            price = flat
        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': False,
        }

    # ------------------------------------------------------------------ #
    # idempotent setup of the single World carrier
    # ------------------------------------------------------------------ #
    @api.model
    def _ensure_world_carrier(self):
        """Create (once) the Uellow World shipping carrier scoped to the World
        website + company. Safe to call repeatedly — returns the existing one."""
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            wid = int(ICP.get_param('uellow_dropship.website_id') or 0)
        except (TypeError, ValueError):
            wid = 0
        if not wid:
            return self.browse()
        website = self.env['website'].sudo().browse(wid)
        if not website.exists():
            return self.browse()
        company = website.company_id or self.env.company

        existing = self.sudo().search(
            [('delivery_type', '=', 'uellow_world')], limit=1)
        if existing:
            # keep it correctly scoped + live
            existing.sudo().write({
                'website_id': wid,
                'company_id': company.id,
                'active': True,
                'is_published': True,
            })
            return existing

        # a service product for the delivery line
        Product = self.env['product.product'].sudo()
        ship_prod = Product.search(
            [('default_code', '=', 'UELLOW_WORLD_SHIP')], limit=1)
        if not ship_prod:
            ship_prod = Product.create({
                'name': 'Uellow World Shipping',
                'default_code': 'UELLOW_WORLD_SHIP',
                'type': 'service',
                'categ_id': self.env.ref(
                    'delivery.product_category_deliveries',
                    raise_if_not_found=False).id
                    if self.env.ref('delivery.product_category_deliveries',
                                    raise_if_not_found=False) else False,
                'sale_ok': False,
                'purchase_ok': False,
                'list_price': 0.0,
                'company_id': False,
            })
        return self.sudo().create({
            'name': 'International Shipping (from China)',
            'delivery_type': 'uellow_world',
            'product_id': ship_prod.id,
            'website_id': wid,
            'company_id': company.id,
            'active': True,
            'is_published': True,
            'sequence': 1,
        })
