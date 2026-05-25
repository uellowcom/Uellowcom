# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _process_pos_ui_product_product(self, products, config_id):
        """
        Odoo 18: inject Arabic product name from translation system.
        Called by pos.session._load_pos_data after loading all products.
        """
        result = super()._process_pos_ui_product_product(products, config_id)

        _logger.warning("Uellow: _process_pos_ui_product_product called with %d products", len(result or []))

        products_list = result if result is not None else products
        if not products_list:
            return result

        # Find active Arabic language
        ar_lang = self.env['res.lang'].search([
            ('code', 'like', 'ar'),
            ('active', '=', True),
        ], limit=1)

        _logger.warning("Uellow: Arabic lang found: %s", ar_lang.code if ar_lang else "NONE")

        if not ar_lang:
            return result

        # Get product IDs
        product_ids = [
            p['id'] for p in products_list
            if isinstance(p, dict) and p.get('id')
        ]
        if not product_ids:
            return result

        # Single DB query for all Arabic names
        ar_name_map = {
            p.id: p.name
            for p in self.env['product.product'].with_context(
                lang=ar_lang.code
            ).browse(product_ids)
        }

        # Inject name_arabic into each product dict
        injected = 0
        for product in products_list:
            if not isinstance(product, dict):
                continue
            pid = product.get('id')
            if pid:
                ar_name = ar_name_map.get(pid, '') or ''
                orig = product.get('display_name') or product.get('name') or ''
                product['name_arabic'] = ar_name if ar_name != orig else ''
                if product['name_arabic']:
                    injected += 1

        _logger.warning("Uellow: Injected Arabic names for %d/%d products", injected, len(product_ids))
        return result


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_pos_data(self, data):
        """Override to verify our module is running."""
        _logger.warning("Uellow: _load_pos_data called")
        return super()._load_pos_data(data)
