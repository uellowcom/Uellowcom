# -*- coding: utf-8 -*-
"""
mobile.flash.sale — Powerful flash-sale block for the app home screen.

Three sourcing modes:
  • manual:        editor picks specific products
  • multivendor:   pulls products vendors flagged as flash-sale in the
                   multivendor module (uellow_vendor)
  • auto_discount: any product with compare_list_price > list_price by
                   at least min_discount_pct

Display + countdown:
  • countdown timer drawn from end_date — server returns ISO; app
    renders the seconds-since-load locally
  • progress bar of stock sold (when sold_count_visible)
  • per-product max_qty_per_user enforcement at /cart/add time

Multi-country aware: each sale has a website_id; the app only sees
sales for its current country website.
"""
from datetime import datetime

from odoo import api, fields, models


class MobileFlashSale(models.Model):
    _name = 'mobile.flash.sale'
    _description = 'Mobile Flash Sale'
    _order = 'sequence, end_date desc'

    name = fields.Char(string='Title (EN)', required=True)
    name_ar = fields.Char(string='Title (AR)')
    subtitle = fields.Char(string='Subtitle (EN)')
    subtitle_ar = fields.Char(string='Subtitle (AR)')

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1),
        help='Which mobile-app website this sale shows on. Country-specific.',
    )

    # ── Schedule ─────────────────────────────────────────────────────
    start_date = fields.Datetime(string='Starts', default=fields.Datetime.now)
    end_date   = fields.Datetime(string='Ends')

    # ── Sourcing ─────────────────────────────────────────────────────
    source = fields.Selection([
        ('manual',         'Manual selection'),
        ('multivendor',    'Vendor-flagged (multi-vendor)'),
        ('auto_discount',  'Auto: any product with discount %'),
    ], string='Source', default='manual', required=True)

    product_ids = fields.Many2many(
        'product.template', string='Manual Products',
        help='Only used when source=manual.',
    )
    min_discount_pct = fields.Integer(
        string='Min Discount %', default=20,
        help='Used when source=auto_discount.',
    )
    max_products = fields.Integer(default=24)

    # ── Per-product limits ───────────────────────────────────────────
    max_qty_per_user = fields.Integer(
        string='Max Qty / Customer', default=0,
        help='0 = no limit. Enforced at cart-add.',
    )

    # ── Display ──────────────────────────────────────────────────────
    display_style = fields.Selection([
        ('grid_2',  '2 columns grid'),
        ('grid_3',  '3 columns grid'),
        ('horizontal', 'Horizontal scroll'),
        ('feature',    'Featured (1 large + small list)'),
    ], default='horizontal', required=True)
    background_color = fields.Char(default='#F5C320')
    accent_color     = fields.Char(default='#FF4D4D')
    show_countdown   = fields.Boolean(default=True)
    show_progress    = fields.Boolean(
        string='Show Sold Progress Bar', default=True,
    )
    show_view_more   = fields.Boolean(default=True)

    # ── Counters ─────────────────────────────────────────────────────
    sold_count = fields.Integer(
        string='Sold Count', compute='_compute_sold_count', store=False,
    )
    is_live    = fields.Boolean(compute='_compute_is_live')

    @api.depends('start_date', 'end_date', 'active')
    def _compute_is_live(self):
        now = datetime.now()
        for rec in self:
            rec.is_live = bool(
                rec.active and
                (not rec.start_date or rec.start_date <= now) and
                (not rec.end_date or rec.end_date >= now)
            )

    def _compute_sold_count(self):
        for rec in self:
            try:
                pids = rec._resolved_products().ids
                if not pids:
                    rec.sold_count = 0
                    continue
                rows = self.env['sale.order.line'].sudo().read_group(
                    domain=[
                        ('product_id.product_tmpl_id', 'in', pids),
                        ('order_id.state', 'in', ['sale', 'done']),
                        ('order_id.date_order', '>=', rec.start_date or datetime.min),
                    ],
                    fields=['product_uom_qty:sum'], groupby=[],
                )
                rec.sold_count = int(rows[0]['product_uom_qty'] or 0) if rows else 0
            except Exception:
                rec.sold_count = 0

    # ── Product resolution ───────────────────────────────────────────
    def _resolved_products(self):
        """Return the product.template recordset that this sale exposes,
        respecting the chosen source + max_products."""
        self.ensure_one()
        Tmpl = self.env['product.template'].sudo()
        domain = [
            ('is_published', '=', True), ('active', '=', True),
            '|', ('website_id', '=', False),
                 ('website_id', '=', self.website_id.id),
        ]

        if self.source == 'manual':
            recs = self.product_ids.filtered(lambda p: p.is_published and p.active)
        elif self.source == 'multivendor':
            # Vendors mark products with a "flash sale" flag on their side.
            # We support either:
            #   product.template.is_flash_sale  (boolean)
            #   product.template.flash_sale_until (datetime)
            # whichever exists in this DB.
            extra = []
            if 'is_flash_sale' in Tmpl._fields:
                extra.append(('is_flash_sale', '=', True))
            elif 'flash_sale_until' in Tmpl._fields:
                extra.append(('flash_sale_until', '>=', datetime.now()))
            else:
                # No vendor-flag field; fall back to auto_discount logic
                extra.append(('compare_list_price', '>', 0))
            recs = Tmpl.search(domain + extra,
                               limit=self.max_products or 50,
                               order='create_date desc')
        else:  # auto_discount
            recs = Tmpl.search(
                domain + [('compare_list_price', '>', 0)],
                limit=self.max_products or 50,
                order='create_date desc',
            )
            recs = recs.filtered(lambda p: p.compare_list_price > 0 and
                                 (1 - p.list_price / p.compare_list_price) * 100 >=
                                 (self.min_discount_pct or 0))

        return recs[:self.max_products] if self.max_products else recs
