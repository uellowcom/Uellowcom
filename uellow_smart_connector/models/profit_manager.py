# -*- coding: utf-8 -*-
"""
Profit Margin Manager — a single screen listing every product with cost,
sale price, profit amount, margin %, installment (Taly/BNPL) eligibility and
website availability.  Lets the manager spot the least/most profitable items
and change a sale price or toggle availability inline.

All maths happen server-side so the UI stays a thin, fast table.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError


class ProfitManager(models.TransientModel):
    _name = 'uellow.sc.profit'
    _description = 'Smart Connector — Profit Margin Manager'

    # ── BNPL / installment eligibility (mirrors api_v2 products._bnpl_offer) ──
    def _bnpl_ctx(self):
        """Return (enabled, min_price) for installment eligibility."""
        Brain = self.env.get('uellow.brain.config')
        try:
            if Brain is None or not Brain.sudo().is_on('bnpl_enabled'):
                return (False, 0.0)
            cfg = Brain.sudo().get_config()
            return (True, float(cfg.bnpl_min_price or 0.0))
        except Exception:
            return (False, 0.0)

    @api.model
    def get_profit_data(self, search='', filt='all', sort='margin_asc',
                        offset=0, limit=40):
        """Return KPI stats + a page of product rows.

        Stats are computed over the WHOLE filtered set; only the rows are
        paginated.  Reads a handful of fields for every product (cheap even
        for a few thousand SKUs) and does the margin maths in Python so we can
        sort/filter on the derived values.
        """
        Product = self.env['product.template'].sudo()
        bnpl_on, bnpl_min = self._bnpl_ctx()

        # base domain — real, sellable, active products
        domain = [('active', '=', True), ('sale_ok', '=', True)]
        s = (search or '').strip()
        if s:
            domain += ['|', ('name', 'ilike', s), ('default_code', 'ilike', s)]
        # field-level pre-filters
        if filt == 'available':
            domain.append(('website_published', '=', True))
        elif filt == 'unavailable':
            domain.append(('website_published', '=', False))
        elif filt == 'installment' and bnpl_on:
            domain.append(('list_price', '>=', bnpl_min))

        recs = Product.search_read(
            domain,
            ['id', 'name', 'default_code', 'list_price', 'standard_price',
             'website_published'],
            limit=20000)

        rows = []
        for r in recs:
            price = r['list_price'] or 0.0
            cost = r['standard_price'] or 0.0
            profit = price - cost
            margin = (profit / price * 100.0) if price > 0 else 0.0
            inst = bool(bnpl_on and price > 0 and price >= bnpl_min)
            rows.append({
                'id': r['id'],
                'name': r['name'] or '',
                'code': r['default_code'] or '',
                'cost': round(cost, 3),
                'price': round(price, 3),
                'profit': round(profit, 3),
                'margin': round(margin, 1),
                'installment': inst,
                'available': bool(r['website_published']),
            })

        # derived-value filters
        if filt == 'negative':
            rows = [x for x in rows if x['profit'] < 0]
        elif filt == 'low':
            rows = [x for x in rows if 0 <= x['margin'] < 10]
        elif filt == 'high':
            rows = [x for x in rows if x['margin'] >= 40]
        elif filt == 'installment' and not bnpl_on:
            rows = []  # installments globally off → none eligible

        # stats over the full filtered set
        total = len(rows)
        sum_profit = sum(x['profit'] for x in rows)
        sum_cost = sum(x['cost'] for x in rows)
        sum_sale = sum(x['price'] for x in rows)
        avg_margin = (sum(x['margin'] for x in rows) / total) if total else 0.0
        stats = {
            'count': total,
            'avg_margin': round(avg_margin, 1),
            'total_profit': round(sum_profit, 3),
            'total_cost': round(sum_cost, 3),
            'total_sale': round(sum_sale, 3),
            'negative': sum(1 for x in rows if x['profit'] < 0),
            'low': sum(1 for x in rows if 0 <= x['margin'] < 10),
            'installment': sum(1 for x in rows if x['installment']),
            'available': sum(1 for x in rows if x['available']),
            'bnpl_on': bnpl_on,
            'bnpl_min': round(bnpl_min, 3),
        }

        # sort
        keymap = {
            'margin_asc':  (lambda x: x['margin'], False),
            'margin_desc': (lambda x: x['margin'], True),
            'profit_asc':  (lambda x: x['profit'], False),
            'profit_desc': (lambda x: x['profit'], True),
            'price_desc':  (lambda x: x['price'], True),
            'name_asc':    (lambda x: (x['name'] or '').lower(), False),
        }
        key, rev = keymap.get(sort, keymap['margin_asc'])
        rows.sort(key=key, reverse=rev)

        # paginate
        offset = max(0, int(offset or 0))
        limit = max(1, min(int(limit or 40), 200))
        page = rows[offset:offset + limit]

        return {
            'stats': stats,
            'rows': page,
            'offset': offset,
            'limit': limit,
            'total': total,
        }

    @api.model
    def set_price(self, product_id, new_price):
        """Change a product's sale price; returns the recomputed row."""
        try:
            price = float(new_price)
        except (TypeError, ValueError):
            raise UserError(_('Enter a valid number.'))
        if price < 0:
            raise UserError(_('Price cannot be negative.'))
        prod = self.env['product.template'].sudo().browse(int(product_id))
        if not prod.exists():
            raise UserError(_('Product not found.'))
        prod.list_price = price
        return self._row(prod)

    @api.model
    def toggle_available(self, product_id):
        """Flip website availability; returns the recomputed row."""
        prod = self.env['product.template'].sudo().browse(int(product_id))
        if not prod.exists():
            raise UserError(_('Product not found.'))
        prod.website_published = not prod.website_published
        return self._row(prod)

    def _row(self, prod):
        bnpl_on, bnpl_min = self._bnpl_ctx()
        price = prod.list_price or 0.0
        cost = prod.standard_price or 0.0
        profit = price - cost
        margin = (profit / price * 100.0) if price > 0 else 0.0
        return {
            'id': prod.id,
            'name': prod.name or '',
            'code': prod.default_code or '',
            'cost': round(cost, 3),
            'price': round(price, 3),
            'profit': round(profit, 3),
            'margin': round(margin, 1),
            'installment': bool(bnpl_on and price > 0 and price >= bnpl_min),
            'available': bool(prod.website_published),
        }
