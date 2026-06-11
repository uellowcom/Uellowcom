# -*- coding: utf-8 -*-
"""
🌟 New-Customer Zone API (v2.2.11)
==================================
- GET /api/mobile/v2/newcustomer/offer     — hero config + eligibility
- GET /api/mobile/v2/newcustomer/products  — paginated product feed

Eligibility states:
  guest     — not logged in → page shows a "register to unlock" CTA
  eligible  — logged in, ZERO confirmed orders → full offer + coupon
  existing  — has orders → may browse (per setting) but no coupon
"""
import logging

from odoo import http
from odoo.http import request

from ._common import (ok, safe_endpoint, current_partner, get_website,
                      get_lang)

_logger = logging.getLogger(__name__)


def _eligibility(env):
    partner = current_partner()
    if not partner:
        return 'guest'
    n = env['sale.order'].sudo().search_count([
        ('partner_id', '=', partner.id),
        ('state', 'in', ('sale', 'done')),
    ])
    return 'eligible' if n == 0 else 'existing'


def _offer_domain(offer, env):
    dom = [('sale_ok', '=', True), ('is_published', '=', True),
           '|', ('is_storable', '=', False),
           '|', ('allow_out_of_stock_order', '=', True),
           ('qty_available', '>', 0)]
    if offer.source == 'manual':
        dom.append(('id', 'in', offer.product_ids.ids or [0]))
    elif offer.source == 'categories':
        dom.append(('public_categ_ids', 'child_of',
                    offer.categ_ids.ids or [0]))
    else:   # discounted
        dom += [('compare_list_price', '>', 0)]
    return dom


def _offer_dict(offer, env):
    state = _eligibility(env)
    show_coupon = state == 'eligible' and bool(offer.coupon_code)
    return {
        'enabled': True,
        'eligibility': state,
        'browse_allowed': state != 'existing' or offer.show_to_existing,
        'title': {'en': offer.title_en or '', 'ar': offer.title_ar or ''},
        'subtitle': {'en': offer.subtitle_en or '',
                     'ar': offer.subtitle_ar or ''},
        'emoji': offer.emoji or '🎁',
        'c1': offer.color_1 or '#7C3AED',
        'c2': offer.color_2 or '#2563EB',
        'text_color': offer.text_color or '#FFFFFF',
        'discount_pct': offer.discount_pct or 0,
        'coupon_code': offer.coupon_code if show_coupon else '',
        'ends_at': offer.ends_at.isoformat() if offer.ends_at else None,
    }


class UellowNewCustomerController(http.Controller):

    @http.route('/api/mobile/v2/newcustomer/offer', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def offer(self, **kw):
        env = request.env
        website = get_website()
        offer = env['mobile.newcustomer.offer'].get_offer(
            website.id if website else None)
        if not offer:
            return ok({'enabled': False})
        return ok(_offer_dict(offer, env))

    @http.route('/api/mobile/v2/newcustomer/products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def products(self, **kw):
        env = request.env
        website = get_website()
        offer = env['mobile.newcustomer.offer'].get_offer(
            website.id if website else None)
        if not offer:
            return ok({'products': [], 'has_more': False})
        from .products import serialize_product_card
        page = max(1, int(kw.get('page', 1) or 1))
        per = min(24, max(6, int(kw.get('per_page', 12) or 12)))
        cap = offer.max_products or 120
        Tmpl = env['product.template'].sudo()
        if website:
            Tmpl = Tmpl.with_context(website_id=website.id)
        dom = _offer_domain(offer, env)
        # site visibility (multi-website)
        if website:
            dom += ['|', ('website_id', '=', False),
                    ('website_id', '=', website.id)]
        offset = (page - 1) * per
        if offset >= cap:
            return ok({'products': [], 'has_more': False, 'page': page})
        limit = min(per, cap - offset)
        recs = Tmpl.search(dom, order='compare_list_price desc, write_date desc',
                           limit=limit + 1, offset=offset)
        has_more = len(recs) > limit and (offset + limit) < cap
        lang = get_lang()
        cards = []
        for t in recs[:limit]:
            try:
                c = serialize_product_card(t, lang)
                if c:
                    cards.append(c)
            except Exception:
                continue
        return ok({'products': cards, 'has_more': has_more, 'page': page})
