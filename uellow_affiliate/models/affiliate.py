# -*- coding: utf-8 -*-
"""Core affiliate models: agent, assignments, commission ledger, payouts."""
import secrets
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


TIERS = [
    ('bronze', '🥉 Bronze'),
    ('silver', '🥈 Silver'),
    ('gold', '🥇 Gold'),
    ('platinum', '💎 Platinum'),
]
# tier → (commission multiplier, monthly confirmed sales needed to reach)
TIER_RULES = {
    'bronze':   (1.00, 0),
    'silver':   (1.10, 500),
    'gold':     (1.25, 2000),
    'platinum': (1.40, 6000),
}


class UellowAffiliate(models.Model):
    _name = 'uellow.affiliate'
    _description = 'Uellow affiliate agent'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(string='Referral Code', required=True, copy=False,
                       index=True,
                       default=lambda self: self._generate_code())
    partner_id = fields.Many2one(
        'res.partner', string='Customer Account', required=True,
        ondelete='restrict', index=True,
        help='The customer account this agent signs in with (mobile app).')
    state = fields.Selection([
        ('pending', '⏳ Pending review'),
        ('active', '✅ Active'),
        ('suspended', '🚫 Suspended'),
    ], default='pending', required=True, tracking=True, index=True)
    tier = fields.Selection(TIERS, default='bronze', required=True,
                            tracking=True)
    default_commission_pct = fields.Float(
        string='Default Commission %', default=5.0,
        help='Used when no product/category assignment matches.')
    phone = fields.Char()
    email = fields.Char()
    website_ids = fields.Many2many(
        'website', 'uellow_affiliate_website_rel',
        'affiliate_id', 'website_id', string='Websites',
        help='Empty = all websites')
    payout_method = fields.Selection([
        ('bank', '🏦 Bank transfer'),
        ('knet', '💳 KNET / local transfer'),
        ('wallet', '👛 Uellow wallet credit'),
    ], default='wallet')
    payout_details = fields.Char(
        help='IBAN / phone number / whatever the chosen method needs.')
    note = fields.Text()

    assignment_ids = fields.One2many('uellow.affiliate.assignment',
                                     'affiliate_id', string='Assignments')
    commission_ids = fields.One2many('uellow.affiliate.commission',
                                     'affiliate_id')
    payout_ids = fields.One2many('uellow.affiliate.payout', 'affiliate_id')
    submitted_order_ids = fields.One2many('uellow.affiliate.order',
                                          'affiliate_id')

    # ── live balances ──
    pending_amount = fields.Monetary(compute='_compute_amounts',
                                     currency_field='currency_id')
    confirmed_amount = fields.Monetary(compute='_compute_amounts',
                                       currency_field='currency_id')
    paid_amount = fields.Monetary(compute='_compute_amounts',
                                  currency_field='currency_id')
    available_amount = fields.Monetary(compute='_compute_amounts',
                                       currency_field='currency_id',
                                       string='Available for payout')
    total_sales = fields.Monetary(compute='_compute_amounts',
                                  currency_field='currency_id',
                                  string='Delivered sales (all time)')
    order_count = fields.Integer(compute='_compute_amounts')
    click_count = fields.Integer(default=0, string='Link opens')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Referral code must be unique'),
        ('partner_uniq', 'unique(partner_id)',
         'This customer is already an affiliate'),
    ]

    @api.model
    def _generate_code(self):
        for _ in range(20):
            code = 'U' + secrets.token_hex(3).upper()
            if not self.search_count([('code', '=', code)]):
                return code
        return 'U' + secrets.token_hex(5).upper()

    def _compute_amounts(self):
        for a in self:
            comms = a.commission_ids
            a.pending_amount = sum(c.amount for c in comms
                                   if c.state == 'pending')
            a.confirmed_amount = sum(c.amount for c in comms
                                     if c.state == 'confirmed')
            a.paid_amount = sum(c.amount for c in comms if c.state == 'paid')
            a.available_amount = a.confirmed_amount
            a.total_sales = sum(c.base_amount for c in comms
                                if c.state in ('confirmed', 'paid'))
            a.order_count = len(comms)

    # ── commission resolution: product assignment > category assignment
    #    (parents walk) > affiliate default; tier multiplier applies on
    #    top in all cases. ──
    def commission_pct_for(self, product_tmpl):
        self.ensure_one()
        pct = None
        prod_rows = self.assignment_ids.filtered(
            lambda r: r.active and r.product_tmpl_id
            and r.product_tmpl_id.id == product_tmpl.id)
        if prod_rows:
            pct = max(prod_rows.mapped('commission_pct'))
        if pct is None:
            cat_rows = self.assignment_ids.filtered(
                lambda r: r.active and r.categ_id)
            if cat_rows:
                cat_ids = set()
                for c in product_tmpl.public_categ_ids:
                    node = c
                    while node:
                        cat_ids.add(node.id)
                        node = node.parent_id
                hits = cat_rows.filtered(lambda r: r.categ_id.id in cat_ids)
                if hits:
                    pct = max(hits.mapped('commission_pct'))
        if pct is None:
            pct = self.default_commission_pct or 0.0
        mult = TIER_RULES.get(self.tier, (1.0, 0))[0]
        return pct * mult

    def allowed_product_domain(self):
        """Domain of products this affiliate may sell. No assignments at
        all = the whole published catalog (full-catalog agent)."""
        self.ensure_one()
        rows = self.assignment_ids.filtered('active')
        if not rows:
            return [('is_published', '=', True), ('sale_ok', '=', True)]
        dom = ['|'] * (len(rows) - 1) if len(rows) > 1 else []
        for r in rows:
            if r.product_tmpl_id:
                dom.append(('id', '=', r.product_tmpl_id.id))
            else:
                dom.append(('public_categ_ids', 'child_of', r.categ_id.id))
        return [('is_published', '=', True), ('sale_ok', '=', True)] + dom

    # ── actions ──
    def action_activate(self):
        self.write({'state': 'active'})

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_recompute_tier(self):
        """Auto-upgrade tier from the last 30 days of CONFIRMED sales."""
        since = fields.Datetime.now() - timedelta(days=30)
        for a in self:
            sales = sum(c.base_amount for c in a.commission_ids
                        if c.state in ('confirmed', 'paid')
                        and c.create_date and c.create_date >= since)
            new_tier = 'bronze'
            for tier, (_m, need) in TIER_RULES.items():
                if sales >= need:
                    new_tier = tier
            order = ['bronze', 'silver', 'gold', 'platinum']
            # upgrades only — never auto-downgrade an agent
            if order.index(new_tier) > order.index(a.tier):
                a.tier = new_tier


class UellowAffiliateAssignment(models.Model):
    _name = 'uellow.affiliate.assignment'
    _description = 'Affiliate product/category assignment'
    _order = 'id desc'

    affiliate_id = fields.Many2one('uellow.affiliate', required=True,
                                   ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product',
                                      ondelete='cascade')
    categ_id = fields.Many2one('product.public.category', string='Category',
                               ondelete='cascade')
    commission_pct = fields.Float(string='Commission %', default=5.0,
                                  required=True)
    active = fields.Boolean(default=True)

    @api.constrains('product_tmpl_id', 'categ_id')
    def _check_target(self):
        for r in self:
            if not r.product_tmpl_id and not r.categ_id:
                raise UserError('Pick a product OR a category.')


class UellowAffiliateCommission(models.Model):
    _name = 'uellow.affiliate.commission'
    _description = 'Affiliate commission ledger entry'
    _order = 'create_date desc'

    affiliate_id = fields.Many2one('uellow.affiliate', required=True,
                                   ondelete='cascade', index=True)
    sale_order_id = fields.Many2one('sale.order', ondelete='set null',
                                    index=True)
    source = fields.Selection([
        ('link', '🔗 Referral link'),
        ('submitted', '📝 Submitted order'),
        ('bonus', '🎁 Bonus'),
        ('adjustment', '✏️ Manual adjustment'),
    ], default='link', required=True)
    base_amount = fields.Monetary(string='Order base (untaxed)',
                                  currency_field='currency_id')
    amount = fields.Monetary(string='Commission',
                             currency_field='currency_id')
    state = fields.Selection([
        ('pending', '⏳ Pending delivery'),
        ('confirmed', '✅ Confirmed'),
        ('paid', '💸 Paid'),
        ('cancelled', '❌ Cancelled'),
    ], default='pending', required=True, index=True)
    payout_id = fields.Many2one('uellow.affiliate.payout',
                                ondelete='set null')
    note = fields.Char()
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    def action_confirm(self):
        self.filtered(lambda c: c.state == 'pending').write(
            {'state': 'confirmed'})

    def action_cancel(self):
        self.filtered(lambda c: c.state in ('pending', 'confirmed')).write(
            {'state': 'cancelled'})

    # ── delivery watcher (cron) — confirm pending commissions whose
    #    order is delivered; cancel those whose order died. ──
    @api.model
    def cron_confirm_delivered(self):
        pend = self.search([('state', '=', 'pending'),
                            ('sale_order_id', '!=', False)])
        for c in pend:
            so = c.sale_order_id
            if so.state == 'cancel':
                c.state = 'cancelled'
                continue
            if self._order_is_delivered(so):
                c.state = 'confirmed'
        # monthly-ish tier recompute piggybacks on the same cron
        self.env['uellow.affiliate'].search(
            [('state', '=', 'active')]).action_recompute_tier()

    @api.model
    def _order_is_delivered(self, so):
        try:
            if getattr(so, 'delivery_status', '') == 'delivered':
                return True
        except Exception:
            pass
        try:
            pickings = so.picking_ids.filtered(
                lambda p: p.picking_type_code == 'outgoing')
            if pickings and all(p.state == 'done' for p in pickings):
                return True
        except Exception:
            pass
        return False


class UellowAffiliatePayout(models.Model):
    _name = 'uellow.affiliate.payout'
    _description = 'Affiliate payout request'
    _order = 'create_date desc'

    name = fields.Char(default=lambda self: self.env['ir.sequence']
                       .next_by_code('uellow.affiliate.payout') or 'PAYOUT')
    affiliate_id = fields.Many2one('uellow.affiliate', required=True,
                                   ondelete='cascade', index=True)
    amount = fields.Monetary(required=True, currency_field='currency_id')
    method = fields.Selection([
        ('bank', '🏦 Bank transfer'),
        ('knet', '💳 KNET / local transfer'),
        ('wallet', '👛 Uellow wallet credit'),
    ], required=True, default='wallet')
    details = fields.Char(help='IBAN / phone / target account.')
    state = fields.Selection([
        ('requested', '⏳ Requested'),
        ('paid', '✅ Paid'),
        ('rejected', '❌ Rejected'),
    ], default='requested', required=True, index=True)
    note = fields.Char()
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    def action_mark_paid(self):
        for p in self:
            if p.state != 'requested':
                continue
            # consume CONFIRMED commissions up to the payout amount
            remaining = p.amount
            comms = self.env['uellow.affiliate.commission'].search([
                ('affiliate_id', '=', p.affiliate_id.id),
                ('state', '=', 'confirmed'),
            ], order='create_date asc')
            for c in comms:
                if remaining <= 0:
                    break
                c.write({'state': 'paid', 'payout_id': p.id})
                remaining -= c.amount
            p.state = 'paid'
            # wallet method → credit the live customer wallet if present
            if p.method == 'wallet':
                try:
                    Wallet = self.env.get('uellow.wallet')
                    if Wallet is not None:
                        Wallet.sudo().credit(
                            p.affiliate_id.partner_id,
                            p.amount, 'Affiliate payout %s' % p.name)
                except Exception:
                    pass

    def action_reject(self):
        self.filtered(lambda p: p.state == 'requested').write(
            {'state': 'rejected'})
