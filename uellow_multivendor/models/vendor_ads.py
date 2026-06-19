# -*- coding: utf-8 -*-
"""Sponsored listings — vendors pay (from wallet) to boost a product.

Activation charges the vendor wallet (days × daily rate) and flags the
product `is_sponsored`. A daily cron expires finished campaigns. The
storefront/app can read `is_sponsored` to rank or badge boosted products.
"""
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorAdCampaign(models.Model):
    _name = 'vendor.ad.campaign'
    _description = 'Sponsored Listing Campaign'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Campaign', required=True, default='Sponsored listing')
    vendor_id = fields.Many2one('uellow.vendor', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product',
                                      ondelete='cascade')
    # ── Format & placement ──────────────────────────────────────────
    ad_format = fields.Selection([
        ('product_boost', 'Product boost (rank + badge)'),
        ('banner',        'Banner ad'),
        ('infeed',        'In-feed card (between products)'),
    ], default='product_boost', required=True, string='Format', index=True)
    placement = fields.Selection([
        ('home',     'Home'),
        ('category', 'Category'),
        ('search',   'Search results'),
        ('all',      'Everywhere'),
    ], default='home', string='Placement')
    target_category_id = fields.Many2one('product.public.category', 'Target Category')
    banner_image = fields.Image('Banner Image', max_width=1600, max_height=900)
    headline = fields.Char('Headline')
    # Link to the live mobile-app ad created when a banner/infeed runs.
    mobile_ad_id = fields.Many2one('mobile.app.ad', 'Live App Ad', readonly=True, copy=False)
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    end_date = fields.Date(required=True)
    daily_rate = fields.Float('Daily Rate', readonly=True,
                              help='KD/day charged, captured from settings at activation.')
    days = fields.Integer('Days', compute='_compute_cost', store=True)
    total_cost = fields.Float('Total Cost', compute='_compute_cost', store=True)
    state = fields.Selection([
        ('draft',  'Draft'),
        ('active', 'Active'),
        ('ended',  'Ended'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, index=True)
    charged = fields.Boolean('Wallet Charged', readonly=True)
    impressions = fields.Integer(readonly=True)
    clicks = fields.Integer(readonly=True)

    @api.depends('start_date', 'end_date', 'daily_rate', 'ad_format')
    def _compute_cost(self):
        for c in self:
            rate = c.daily_rate or c._quote_rate()
            if c.start_date and c.end_date and c.end_date >= c.start_date:
                c.days = (c.end_date - c.start_date).days + 1
            else:
                c.days = 0
            c.total_cost = c.days * rate

    def _quote_rate(self):
        """Daily rate by format (banner > infeed > product boost)."""
        P = self.env['ir.config_parameter'].sudo()
        base = float(P.get_param('uellow.vendor_api.ad_daily_rate', '1.0') or 1.0)
        mult = {
            'product_boost': float(P.get_param('uellow.vendor_api.ad_rate_boost', '1.0') or 1.0),
            'banner':        float(P.get_param('uellow.vendor_api.ad_rate_banner', '3.0') or 3.0),
            'infeed':        float(P.get_param('uellow.vendor_api.ad_rate_infeed', '2.0') or 2.0),
        }.get(self.ad_format or 'product_boost', 1.0)
        return round(base * mult, 3)

    def action_activate(self):
        for c in self.filtered(lambda r: r.state == 'draft'):
            if not c.end_date or c.end_date < (c.start_date or fields.Date.context_today(c)):
                raise UserError(_('End date must be on or after the start date.'))
            if c.product_tmpl_id and c.product_tmpl_id.vendor_id.id != c.vendor_id.id:
                raise UserError(_('Product does not belong to this vendor.'))
            if c.ad_format == 'product_boost' and not c.product_tmpl_id:
                raise UserError(_('Select a product to boost.'))
            if c.ad_format in ('banner', 'infeed') and not (c.banner_image or c.product_tmpl_id):
                raise UserError(_('Add a banner image or pick a product.'))
            c.daily_rate = c._quote_rate()
            c._compute_cost()
            cost = c.total_cost
            wallet = c.vendor_id.wallet_id
            if not wallet:
                raise UserError(_('Vendor has no wallet to charge.'))
            if cost > 0:
                wallet.debit(cost, description=_('Sponsored ad (%s): %s') % (
                    c.ad_format, c.product_tmpl_id.name or c.name))
            c.charged = True
            c.state = 'active'
            if c.ad_format == 'product_boost' and c.product_tmpl_id:
                c.product_tmpl_id.write({'is_sponsored': True, 'sponsor_until': c.end_date})
            else:
                c._sync_mobile_ad()
            c.message_post(body=_('Campaign activated — charged %.3f from wallet.') % cost)
        return True

    def _sync_mobile_ad(self):
        """Create / refresh the live mobile.app.ad for banner & in-feed formats,
        scoped to the vendor's market websites so it renders in the main app."""
        self.ensure_one()
        Ad = self.env['mobile.app.ad'].sudo()
        ad_type = 'infeed' if self.ad_format == 'infeed' else 'popup'
        # banners ride the in-feed placement as a full-width card; popups for hero
        if self.ad_format == 'banner':
            ad_type = 'infeed'
        vals = {
            'name': 'Vendor: %s' % (self.name or self.product_tmpl_id.name or 'Ad'),
            'ad_type': ad_type,
            'active': True,
            'title_en': self.headline or (self.product_tmpl_id.name if self.product_tmpl_id else ''),
            'date_from': fields.Datetime.now(),
            'date_to': fields.Datetime.to_datetime(self.end_date) if self.end_date else False,
            'link_type': 'product' if self.product_tmpl_id else 'none',
            'target_product_id': self.product_tmpl_id.id if self.product_tmpl_id else False,
            'website_ids': [(6, 0, self.vendor_id._market_website_ids().ids)],
        }
        if self.banner_image:
            vals['image'] = self.banner_image
        if self.mobile_ad_id:
            self.mobile_ad_id.write(vals)
        else:
            self.mobile_ad_id = Ad.create(vals)

    def action_cancel(self):
        for c in self:
            c.state = 'cancelled'
            c._refresh_product_flag()
            if c.mobile_ad_id:
                c.mobile_ad_id.active = False

    def _refresh_product_flag(self):
        """Set product.is_sponsored from any still-active campaign."""
        for c in self:
            if not c.product_tmpl_id:
                continue
            others = self.search([
                ('product_tmpl_id', '=', c.product_tmpl_id.id),
                ('state', '=', 'active'),
                ('id', '!=', c.id),
            ], limit=1)
            if not others:
                c.product_tmpl_id.write({'is_sponsored': False, 'sponsor_until': False})

    @api.model
    def _cron_expire_ads(self):
        today = fields.Date.context_today(self)
        expired = self.search([('state', '=', 'active'), ('end_date', '<', today)])
        for c in expired:
            c.state = 'ended'
            c._refresh_product_flag()
            if c.mobile_ad_id:
                c.mobile_ad_id.active = False
        return True
