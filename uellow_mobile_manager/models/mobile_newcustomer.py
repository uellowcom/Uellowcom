# -*- coding: utf-8 -*-
"""
🌟 New-Customer Zone (v2.2.11)
==============================
A standalone "exclusive for new customers" program — configured from its
own menu next to 🎉 Promotions (NOT a mobile.app.promotion record).

Feeds:
- the dedicated in-app page  /api/mobile/v2/newcustomer/*  (hero, coupon,
  eligibility, product feed)
- the `new-customer-zone` builder block (teaser banner on any page)

Eligibility: a logged-in customer with ZERO confirmed orders. Guests see
the page but are pushed to register; existing customers can browse but
the coupon is hidden (configurable).
"""
from odoo import api, fields, models


class MobileNewCustomerOffer(models.Model):
    _name = 'mobile.newcustomer.offer'
    _description = 'New-Customer Exclusive Zone'
    _rec_name = 'display_label'

    display_label = fields.Char(default='New-Customer Zone', readonly=True)
    enabled = fields.Boolean(default=True)

    # ── hero copy ──
    title_en = fields.Char(default='Exclusive for New Customers')
    title_ar = fields.Char(default='حصري للعملاء الجدد')
    subtitle_en = fields.Char(
        default='Welcome gift — special prices on your first order')
    subtitle_ar = fields.Char(
        default='هدية ترحيبية — أسعار خاصة على طلبك الأول')
    emoji = fields.Char(default='🎁')
    color_1 = fields.Char(string='Hero colour 1', default='#7C3AED')
    color_2 = fields.Char(string='Hero colour 2', default='#2563EB')
    text_color = fields.Char(string='Hero text colour', default='#FFFFFF')

    # ── the gift ──
    discount_pct = fields.Integer(
        string='Headline discount %', default=15,
        help='Display-only headline (e.g. "up to 15% OFF").')
    coupon_code = fields.Char(
        string='Welcome coupon code',
        help='Shown with a one-tap copy to ELIGIBLE customers only. '
             'Create the matching code under Loyalty / Coupons.')
    ends_at = fields.Datetime(
        string='Offer deadline (optional)',
        help='Shows a countdown on the page when set.')

    # ── products ──
    source = fields.Selection([
        ('discounted', 'All discounted products'),
        ('categories', 'Specific categories'),
        ('manual', 'Hand-picked products'),
    ], default='discounted', required=True)
    categ_ids = fields.Many2many('product.public.category',
                                 string='Categories')
    product_ids = fields.Many2many('product.template',
                                   string='Hand-picked products',
                                   domain=[('sale_ok', '=', True)])
    max_products = fields.Integer(default=120)

    # ── visibility ──
    website_ids = fields.Many2many(
        'website', string='Websites (empty = all)')
    show_to_existing = fields.Boolean(
        string='Existing customers may browse the page', default=True,
        help='OFF = existing customers get a polite "new customers only" '
             'screen. The coupon is never shown to them either way.')

    @api.model
    def get_offer(self, website_id=None):
        dom = [('enabled', '=', True)]
        recs = self.sudo().search(dom, order='id desc')
        for r in recs:
            if not r.website_ids or not website_id \
                    or website_id in r.website_ids.ids:
                return r
        return self.browse()
