# -*- coding: utf-8 -*-
"""Manual / curated adapter.

A safe default provider that never calls an external API. Products are curated
by hand (or imported from a CSV / the Chrome-extension style flow) straight into
``dropship.product``. Useful for testing the whole pipeline before any real
provider credentials exist, and for one-off curated listings.
"""
from .base import DropshipAdapter, register


@register('manual')
class ManualAdapter(DropshipAdapter):
    code = 'manual'

    def authenticate(self):
        # No remote auth for manual curation.
        return True

    def search_feed(self, query=None, category=None, page=1, page_size=20):
        # Manual products already live in dropship.product; nothing to fetch.
        return []

    def get_product(self, source_id):
        rec = self.env['dropship.product'].search([
            ('provider_id', '=', self.provider.id),
            ('source_id', '=', source_id),
        ], limit=1)
        return rec._to_unified() if rec else None

    def get_freight(self, source_id, country_code, quantity=1):
        # Flat manual shipping estimate from the provider record.
        return [{
            'service': 'manual',
            'cost': self.provider.manual_shipping_cost or 0.0,
            'currency': self.provider.currency or 'USD',
            'days_min': 7,
            'days_max': 20,
        }]

    def place_order(self, order_payload):
        # Manual fulfilment: operator places the order off-platform.
        return {'provider_order_id': False, 'status': 'manual_pending'}

    def get_tracking(self, provider_order_id):
        return {'carrier': False, 'tracking_no': False, 'status': 'manual', 'events': []}
