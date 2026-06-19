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
    logo_image = fields.Binary(string='Store Logo Image')
    banner_image = fields.Binary(string='Store Banner Image')
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

    # ── Market scoping (which storefronts this vendor sells on) ──────────
    market_website_ids = fields.Many2many(
        'website', 'uellow_vendor_market_website_rel', 'vendor_id', 'website_id',
        string='Sales Markets (Websites)',
        help='The storefronts (country web + mobile-app sites) where this '
             "vendor's products are shown. Empty = inherits product defaults.")
    exclusive_markets = fields.Boolean(
        'Exclusive to Markets', default=True,
        help='When on, the vendor\'s products are shown ONLY on the selected '
             'markets (country exclusivity). When off, products keep their own '
             'website visibility.')
    product_market_count = fields.Integer(
        compute='_compute_product_market_count', string='Products')

    def _compute_product_market_count(self):
        Tmpl = self.env['product.template'].sudo()
        for v in self:
            v.product_market_count = Tmpl.search_count([('vendor_id', '=', v.id)])

    def _market_website_ids(self):
        """Resolve the websites this vendor sells on. Falls back to any websites
        whose name matches the vendor's country when no explicit markets set."""
        self.ensure_one()
        if self.market_website_ids:
            return self.market_website_ids
        if self.country_id:
            # Seed from the country↔website map + name match (web + mobile app).
            sites = self.env['website'].sudo()
            try:
                cw = self.env['mobile.country.website'].sudo().search(
                    [('country_id', '=', self.country_id.id)])
                sites |= cw.mapped('website_id')
            except Exception:
                pass
            name = (self.country_id.name or '').strip()
            if name:
                sites |= self.env['website'].sudo().search([('name', 'ilike', name)])
            return sites
        return self.env['website'].sudo()

    def _apply_market_to_product(self, product):
        """Scope a product to the vendor's markets for country exclusivity:
        primary website = first market, the rest become extra websites."""
        self.ensure_one()
        if not self.exclusive_markets:
            return
        sites = self._market_website_ids()
        if not sites:
            return
        sites = sites.sorted('id')
        vals = {'website_id': sites[0].id}
        extra = sites[1:]
        if 'uellow_extra_website_ids' in product._fields:
            vals['uellow_extra_website_ids'] = [(6, 0, extra.ids)]
        product.sudo().write(vals)

    def action_sync_product_markets(self):
        """Backfill: apply the vendor's market scoping to all their products."""
        Tmpl = self.env['product.template'].sudo()
        for v in self:
            if not v.exclusive_markets:
                continue
            for t in Tmpl.search([('vendor_id', '=', v.id)]):
                v._apply_market_to_product(t)
        return True

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

    # ── Products (v2.1.66) ────────────────────────────────
    # Admin can assign ANY existing catalog product to this vendor from
    # the vendor form (widget=many2many picker on this one2many) or from
    # the product form's Vendor field. Assigned products appear on the
    # vendor's storefront in the app.
    product_ids = fields.One2many(
        'product.template', 'vendor_id', string='Products')
    product_total = fields.Integer(
        compute='_compute_product_total', string='Product Count')

    def _compute_product_total(self):
        for v in self:
            v.product_total = self.env['product.template'].sudo() \
                .search_count([('vendor_id', '=', v.id)])

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

    # ── Vendor Score (0-100 composite performance) ───────
    uc_score = fields.Integer(compute='_compute_uc_score', string='Vendor Score')
    uc_score_band = fields.Char(compute='_compute_uc_score', string='Score Band')

    @api.depends('avg_rating', 'cancel_rate', 'order_count')
    def _compute_uc_score(self):
        for v in self:
            rating = (v.avg_rating or 0) / 5.0 * 40.0          # 0-40
            reliability = max(0.0, 30.0 - (v.cancel_rate or 0) * 6.0)  # 0-30
            activity = min(30.0, (v.order_count or 0) * 0.3)   # 0-30
            s = rating + reliability + activity
            v.uc_score = int(round(s))
            v.uc_score_band = ('excellent' if s >= 80 else 'good' if s >= 60
                               else 'fair' if s >= 40 else 'at_risk')

    # ── Settings (overrides from vendor_settings) ────────
    settings_id = fields.Many2one(
        'uellow.vendor.settings', string='Settings',
        ondelete='set null', copy=False,
    )

    # ── Capability & settlement mirrors (editable on the vendor form;
    #    write straight through to settings_id so admins manage everything
    #    from the vendor page). ────────────────────────────
    vendor_type          = fields.Selection(related='settings_id.vendor_type',          readonly=False, store=True)
    capability_preset    = fields.Selection(related='settings_id.capability_preset',    readonly=False)
    cap_add_products     = fields.Boolean(related='settings_id.cap_add_products',     readonly=False)
    cap_edit_products    = fields.Boolean(related='settings_id.cap_edit_products',    readonly=False)
    cap_archive_products = fields.Boolean(related='settings_id.cap_archive_products', readonly=False)
    cap_update_stock     = fields.Boolean(related='settings_id.cap_update_stock',     readonly=False)
    cap_publish_products = fields.Boolean(related='settings_id.cap_publish_products', readonly=False)
    cap_manage_price     = fields.Boolean(related='settings_id.cap_manage_price',     readonly=False)
    cap_flash_sale       = fields.Boolean(related='settings_id.cap_flash_sale',       readonly=False)
    cap_bundles          = fields.Boolean(related='settings_id.cap_bundles',          readonly=False)
    cap_join_promotions  = fields.Boolean(related='settings_id.cap_join_promotions',  readonly=False)
    cap_import_products  = fields.Boolean(related='settings_id.cap_import_products',  readonly=False)
    cap_manage_orders    = fields.Boolean(related='settings_id.cap_manage_orders',    readonly=False)
    cap_cancel_orders    = fields.Boolean(related='settings_id.cap_cancel_orders',    readonly=False)
    cap_accept_orders    = fields.Boolean(related='settings_id.cap_accept_orders',    readonly=False)
    cap_restock          = fields.Boolean(related='settings_id.cap_restock',          readonly=False)
    cap_edit_store       = fields.Boolean(related='settings_id.cap_edit_store',       readonly=False)
    cap_request_payout   = fields.Boolean(related='settings_id.cap_request_payout',   readonly=False)
    cap_api              = fields.Boolean(related='settings_id.cap_api',              readonly=False)
    cap_live             = fields.Boolean(related='settings_id.cap_live',             readonly=False)
    cap_quick_sale       = fields.Boolean(related='settings_id.cap_quick_sale',       readonly=False)
    sla_hours            = fields.Integer(related='settings_id.sla_hours',            readonly=False)
    settlement_mode      = fields.Selection(related='settings_id.settlement_mode',     readonly=False)
    settle_trigger       = fields.Selection(related='settings_id.settle_trigger',      readonly=False)
    hide_financials      = fields.Boolean(related='settings_id.hide_financials',      readonly=False)

    def _ensure_settings(self):
        """Return the vendor's settings record, creating it if missing."""
        self.ensure_one()
        if not self.settings_id:
            self.settings_id = self.env['uellow.vendor.settings'].sudo().create({
                'vendor_id': self.id,
            })
        return self.settings_id

    def cap(self, code):
        """True if the vendor is allowed to perform capability `code`
        (e.g. 'add_products'). No settings record = unrestricted (legacy)."""
        self.ensure_one()
        s = self.settings_id
        if not s:
            return True
        return bool(getattr(s, 'cap_' + code, True))

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
