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
                                      required=True, ondelete='cascade')
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

    @api.depends('start_date', 'end_date', 'daily_rate')
    def _compute_cost(self):
        rate_param = float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow.vendor_api.ad_daily_rate', '1.0') or 1.0)
        for c in self:
            rate = c.daily_rate or rate_param
            if c.start_date and c.end_date and c.end_date >= c.start_date:
                c.days = (c.end_date - c.start_date).days + 1
            else:
                c.days = 0
            c.total_cost = c.days * rate

    def _quote_rate(self):
        return float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow.vendor_api.ad_daily_rate', '1.0') or 1.0)

    def action_activate(self):
        for c in self.filtered(lambda r: r.state == 'draft'):
            if not c.end_date or c.end_date < (c.start_date or fields.Date.context_today(c)):
                raise UserError(_('End date must be on or after the start date.'))
            if c.product_tmpl_id.vendor_id.id != c.vendor_id.id:
                raise UserError(_('Product does not belong to this vendor.'))
            c.daily_rate = c._quote_rate()
            c._compute_cost()
            cost = c.total_cost
            wallet = c.vendor_id.wallet_id
            if not wallet:
                raise UserError(_('Vendor has no wallet to charge.'))
            if cost > 0:
                wallet.debit(cost, description=_('Sponsored listing: %s') % c.product_tmpl_id.name)
            c.charged = True
            c.state = 'active'
            c.product_tmpl_id.write({
                'is_sponsored': True,
                'sponsor_until': c.end_date,
            })
            c.message_post(body=_('Campaign activated — charged %.3f from wallet.') % cost)
        return True

    def action_cancel(self):
        for c in self:
            c.state = 'cancelled'
            c._refresh_product_flag()

    def _refresh_product_flag(self):
        """Set product.is_sponsored from any still-active campaign."""
        for c in self:
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
        return True
