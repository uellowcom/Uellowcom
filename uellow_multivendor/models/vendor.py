import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UellowVendor(models.Model):
    """
    Core vendor record — links a res.partner to their marketplace profile.
    One vendor = one partner = one FBU sub-location (via uellow_fulfillment).
    Supports multi-country and multi-currency.
    """
    _name = 'uellow.vendor'
    _description = 'Marketplace Vendor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'id desc'

    # ── Identity ─────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        required=True, ondelete='restrict', index=True,
    )
    display_name = fields.Char(
        compute='_compute_display_name', store=True,
    )
    user_id = fields.Many2one(
        'res.users', string='Portal User',
        ondelete='set null', index=True,
        help='The portal user who manages this vendor account',
    )

    # ── Store identity ───────────────────────────────────
    store_name_en = fields.Char('Store Name (English)', required=True)
    store_name_ar = fields.Char('Store Name (Arabic)')
    store_slug = fields.Char(
        'Store URL Slug', index=True,
        help='uellow.com/store/{slug}',
    )
    store_description_en = fields.Text('Store Description (English)')
    store_description_ar = fields.Text('Store Description (Arabic)')
    store_tagline_en = fields.Char('Tagline (English)')
    store_tagline_ar = fields.Char('Tagline (Arabic)')

    # ── Branding ─────────────────────────────────────────
    logo_attachment_id = fields.Many2one(
        'ir.attachment', string='Store Logo', ondelete='set null',
    )
    banner_attachment_id = fields.Many2one(
        'ir.attachment', string='Store Banner', ondelete='set null',
    )
    brand_color = fields.Char('Brand Color (hex)', default='#1A7A6E')
    banner_style = fields.Selection([
        ('pattern',  'Pattern'),
        ('solid',    'Solid Color'),
        ('gradient', 'Gradient'),
        ('image',    'Image'),
    ], default='pattern', string='Banner Style')

    # ── Geography & Currency ─────────────────────────────
    country_id = fields.Many2one(
        'res.country', string='Country',
        default=lambda self: self.env.ref('base.kw', raise_if_not_found=False),
    )
    currency_id = fields.Many2one(
        'res.currency', string='Payout Currency',
        default=lambda self: self.env.ref('base.KWD', raise_if_not_found=False),
    )
    timezone = fields.Selection(
        '_tz_get', string='Timezone', default='Asia/Kuwait',
    )

    @api.model
    def _tz_get(self):
        return [(x, x) for x in sorted(
            __import__('pytz').all_timezones, key=lambda tz: tz)]

    # ── Plan & Status ────────────────────────────────────
    plan_id = fields.Many2one(
        'uellow.commission.plan', string='Subscription Plan',
        ondelete='restrict',
    )
    state = fields.Selection([
        ('draft',     'Draft'),
        ('pending',   'Pending Review'),
        ('active',    'Active'),
        ('suspended', 'Suspended'),
        ('rejected',  'Rejected'),
    ], default='draft', string='Status', tracking=True, index=True)

    tier = fields.Selection([
        ('bronze',   'Bronze'),
        ('silver',   'Silver'),
        ('gold',     'Gold'),
        ('platinum', 'Platinum'),
    ], default='bronze', string='Vendor Tier', tracking=True)
    tier_manual = fields.Boolean('Manual Tier Override', default=False)

    # ── Metrics (auto-computed) ───────────────────────────
    total_sales = fields.Float(
        compute='_compute_metrics', store=True, string='Total Sales',
    )
    order_count = fields.Integer(
        compute='_compute_metrics', store=True, string='Orders',
    )
    avg_rating = fields.Float(
        compute='_compute_metrics', store=True, string='Avg Rating',
    )
    follower_count = fields.Integer(
        compute='_compute_follower_count', string='Store Followers',
    )
    cancel_rate = fields.Float(
        compute='_compute_metrics', store=True, string='Cancel Rate (%)',
    )

    # ── Settings (overrides from vendor_settings) ────────
    settings_id = fields.Many2one(
        'uellow.vendor.settings', string='Settings',
        ondelete='set null', copy=False,
    )

    # ── FBU link ─────────────────────────────────────────
    fbu_location_id = fields.Many2one(
        'uellow.vendor.location', string='FBU Sub-warehouse',
        ondelete='set null', copy=False,
    )

    # ── Wallet ───────────────────────────────────────────
    wallet_id = fields.Many2one(
        'uellow.vendor.wallet', string='Wallet',
        ondelete='restrict', copy=False,
    )
    wallet_balance = fields.Float(
        related='wallet_id.balance', string='Wallet Balance',
    )

    # ── Registration fields ──────────────────────────────
    business_name = fields.Char('Legal Business Name')
    commercial_reg = fields.Char('Commercial Registration No.')
    contact_phone = fields.Char('Contact Phone')
    contact_email = fields.Char('Contact Email')
    bank_iban = fields.Char('IBAN')
    bank_name = fields.Char('Bank Name')
    registration_date = fields.Date('Registration Date')
    approval_date = fields.Date('Approval Date')
    rejection_reason = fields.Text('Rejection Reason')

    # ── SLA & Rules ──────────────────────────────────────
    sla_hours = fields.Integer('SLA Hours', default=24)
    max_cancel_rate = fields.Float('Max Cancel Rate (%)', default=5.0)
    max_products = fields.Integer('Max Active Products', default=500)
    sla_action = fields.Selection([
        ('notify',    'Notify Vendor'),
        ('notify_admin', 'Notify + Admin'),
        ('transfer',  'Transfer to Uellow'),
        ('cancel',    'Cancel Order'),
    ], default='notify', string='SLA Breach Action')

    _sql_constraints = [
        ('unique_partner', 'UNIQUE(partner_id)', 'Partner already has a vendor account.'),
        ('unique_slug', 'UNIQUE(store_slug)', 'Store slug must be unique.'),
    ]

    @api.depends('store_name_en', 'partner_id')
    def _compute_display_name(self):
        for v in self:
            v.display_name = v.store_name_en or v.partner_id.name or ''

    def _compute_metrics(self):
        for vendor in self:
            orders = self.env['sale.order'].search([
                ('vendor_id', '=', vendor.id),
                ('state', 'in', ('sale', 'done')),
            ])
            vendor.order_count = len(orders)
            vendor.total_sales = sum(orders.mapped('amount_total'))
            cancelled = self.env['sale.order'].search_count([
                ('vendor_id', '=', vendor.id),
                ('state', '=', 'cancel'),
            ])
            total = vendor.order_count + cancelled
            vendor.cancel_rate = (cancelled / total * 100) if total else 0.0
            # Rating from sale orders
            rated = orders.filtered(lambda o: o.vendor_rating > 0)
            vendor.avg_rating = (
                sum(rated.mapped('vendor_rating')) / len(rated)
            ) if rated else 0.0

    def _compute_follower_count(self):
        for vendor in self:
            vendor.follower_count = self.env['uellow.vendor.follower'].search_count([
                ('vendor_id', '=', vendor.id),
            ])

    @api.model
    def _generate_slug(self, name):
        import re
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[\s_-]+', '-', slug).strip('-')
        # Ensure uniqueness
        base = slug
        counter = 1
        while self.search([('store_slug', '=', slug)]):
            slug = f'{base}-{counter}'
            counter += 1
        return slug

    # ── Lifecycle ────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('store_slug') and vals.get('store_name_en'):
                vals['store_slug'] = self._generate_slug(vals['store_name_en'])
            if not vals.get('registration_date'):
                vals['registration_date'] = fields.Date.today()
        return super().create(vals_list)

    def action_submit(self):
        for v in self:
            if not v.store_name_en:
                raise UserError(_('Store name is required.'))
            v.state = 'pending'

    def action_approve(self):
        for v in self:
            v.state = 'active'
            v.approval_date = fields.Date.today()
            # Create FBU sub-location
            if not v.fbu_location_id:
                fbu = self.env['uellow.vendor.location'].create_for_vendor(v.partner_id)
                v.fbu_location_id = fbu
            # Mark partner as vendor
            v.partner_id.write({
                'is_uellow_vendor': True,
                'vendor_state': 'active',
            })
            # Create wallet if not exists
            if not v.wallet_id:
                wallet = self.env['uellow.vendor.wallet'].create({
                    'vendor_id': v.id,
                    'currency_id': v.currency_id.id,
                })
                v.wallet_id = wallet
            # Create settings if not exists
            if not v.settings_id:
                settings = self.env['uellow.vendor.settings'].create({
                    'vendor_id': v.id,
                })
                v.settings_id = settings
            v.message_post(body=_('Vendor approved. Sub-warehouse and wallet created.'))

    def action_approve_wizard(self):
        """Open approve wizard from button."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approve Vendor',
            'res_model': 'uellow.vendor.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_vendor_id': self.id},
        }

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.vendor.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_vendor_id': self.id},
        }

    def action_suspend(self):
        for v in self:
            v.state = 'suspended'
            v.partner_id.vendor_state = 'suspended'
            if v.fbu_location_id:
                v.fbu_location_id.action_suspend()

    def action_reactivate(self):
        for v in self:
            v.state = 'active'
            v.partner_id.vendor_state = 'active'
            if v.fbu_location_id:
                v.fbu_location_id.action_activate()

    def action_view_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Orders — {self.display_name}',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('vendor_id', '=', self.id)],
        }

    def action_view_wallet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Wallet',
            'res_model': 'uellow.vendor.wallet',
            'view_mode': 'form',
            'res_id': self.wallet_id.id,
        }


class UellowVendorFollower(models.Model):
    """Customers who follow a vendor store."""
    _name = 'uellow.vendor.follower'
    _description = 'Vendor Follower'

    vendor_id = fields.Many2one('uellow.vendor', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    followed_on = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_follow', 'UNIQUE(vendor_id, partner_id)', 'Already following this vendor.'),
    ]
