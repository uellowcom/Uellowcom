# -*- coding: utf-8 -*-
{
    'name': 'Uellow Lamma — Smart Bundle',
    'summary': 'لمّة يلو: smart build-your-bundle with margin-protected dynamic discount',
    'description': """
Uellow Lamma (لمّة يلو)
======================
Customers build a "Lamma" (bundle) from any product; the discount grows as they
add more, but is always protected by a guaranteed minimum profit margin and a max
discount cap — so a Lamma never sells below margin.

Two Lamma types:
  * Normal      — margin-protected tiered discount.
  * Installment — same, but reserves an EXTRA guaranteed margin (default 6.5%)
                  on top of the normal margin to cover installment fees.

Phase 1 (this module): backend config + the pricing engine (pure, tested).
Storefront button / cart / mobile API are wired in later phases.
""",
    'version': '18.0.1.0.0',
    'author': 'Uellow',
    'website': 'https://uellow.com',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'views/lamma_config_views.xml',
    ],
    'installable': True,
    'application': True,
}
