from odoo import models, fields, api, _


class VendorSettings(models.Model):
    """
    Per-vendor settings — intervention level, visibility, shipping rules.
    One settings record per vendor, auto-created on approval.
    """
    _name = 'uellow.vendor.settings'
    _description = 'Vendor Settings'
    _rec_name = 'vendor_id'

    # ── Style / Branding colors (empty = fallback to brand_color, then module default) ──
    flash_bg_color = fields.Char('Flash Sale Background', help='Hex. Empty = brand color')
    flash_accent_color = fields.Char('Flash Sale Accent', help='Hex for timer/badges. Empty = #ffd60a')
    section_title_color = fields.Char('Section Titles Color', help='Hex. Empty = brand color')
    price_color = fields.Char('Price Color', help='Hex. Empty = #1A7A6E')
    badge_color = fields.Char('Discount Badge Color', help='Hex. Empty = #c0392b')
    header_text_color = fields.Char('Header Text Color', help='Hex. Empty = white')

    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )

    # ── Vendor fulfillment type ───────────────────────────
    # The vendor's business model. Acts as a PRESET that sets the
    # fulfillment-related toggles below. Admin can still override any
    # single toggle afterwards (type just seeds sensible defaults).
    vendor_type = fields.Selection([
        ('fbu',          'FBU — Fulfilled by Uellow (stock in Uellow)'),
        ('seller',       'Seller — own stock, Uellow pickup'),
        ('dropshipper',  'Dropshipper — own stock, self-delivery'),
        ('hybrid',       'Hybrid — per-product fulfillment'),
        ('consignment',  'Consignment — stock in Uellow, pay after sale'),
    ], default='seller', string='Vendor Type', index=True,
        help='Business model. Seeds fulfillment toggles (stock control, '
             'customer-data visibility, settlement). Override individually after.')

    def _apply_vendor_type_preset(self):
        """Seed fulfillment toggles from vendor_type. Only touches the
        fulfillment-related fields; leaves the rest of the caps as-is."""
        for s in self:
            t = s.vendor_type
            if t in ('fbu', 'consignment'):
                # Stock physically at Uellow → vendor can't set stock directly,
                # requests restock instead; never sees the end customer.
                s.cap_update_stock = False
                s.cap_restock = True
                s.vendor_sees_customer = False
                s.vendor_can_message = False
                if t == 'consignment':
                    s.settle_trigger = 'deliver'
            elif t == 'seller':
                # Own stock, prepares + prints own label/invoice, Uellow delivers.
                s.cap_update_stock = True
                s.vendor_sees_customer = False
                s.invoice_name = 'vendor'
            elif t == 'dropshipper':
                # Own stock and self-delivery → needs the customer address.
                s.cap_update_stock = True
                s.vendor_sees_customer = True
            elif t == 'hybrid':
                s.cap_update_stock = True

    @api.onchange('vendor_type')
    def _onchange_vendor_type(self):
        self._apply_vendor_type_preset()

    # ── Product settings ─────────────────────────────────
    product_approval = fields.Selection([
        ('manual',    'Manual Review by Uellow'),
        ('ai',        'AI Auto-approve'),
        ('instant',   'Instant (no review)'),
    ], default='manual', string='Product Approval')

    ai_enrich_products = fields.Boolean('AI Enriches Products', default=True)
    allow_smart_connector = fields.Boolean('Allow Smart Connector', default=True)
    allow_flash_sale = fields.Boolean('Allow Flash Sale', default=True)
    allow_bundle = fields.Boolean('Allow Bundle Builder', default=True)
    max_products = fields.Integer('Max Products', default=500)
    unlimited_products = fields.Boolean('Unlimited Products', default=False)
    add_uellow_warranty = fields.Boolean('Add Uellow Warranty', default=True)
    vendor_sets_price = fields.Boolean('Vendor Sets Price Freely', default=True)
    min_price_enabled = fields.Boolean('Min Price Enabled', default=True)

    # ── Capabilities (what the vendor is allowed to DO) ───
    # Each toggle gates a vendor self-service action in the portal AND the
    # vendor mobile API. Default True = unrestricted (legacy behaviour).
    capability_preset = fields.Selection([
        ('full',     'Full self-service'),
        ('managed',  'Managed (limited)'),
        ('readonly', 'Read-only (view only)'),
        ('house',    'House brand (no finance, no self-service)'),
        ('custom',   'Custom'),
    ], default='custom', string='Capability Preset',
        help='Quick profile that sets all capability toggles at once.')

    cap_add_products     = fields.Boolean('Can Add Products', default=True)
    cap_edit_products    = fields.Boolean('Can Edit Products', default=True)
    cap_archive_products = fields.Boolean('Can Archive / Delete Products', default=True)
    cap_update_stock     = fields.Boolean('Can Update Stock', default=True)
    cap_publish_products = fields.Boolean('Can Publish / Unpublish', default=True)
    cap_manage_price     = fields.Boolean('Can Change Prices', default=True)
    cap_flash_sale       = fields.Boolean('Can Run Flash Sales', default=True)
    cap_bundles          = fields.Boolean('Can Build Bundles', default=True)
    cap_join_promotions  = fields.Boolean('Can Join Promotions', default=True)
    cap_import_products  = fields.Boolean('Can Import Products (file/URL)', default=True)
    cap_manage_orders    = fields.Boolean('Can Manage Orders (confirm/ship)', default=True)
    cap_cancel_orders    = fields.Boolean('Can Cancel Orders', default=True)
    cap_restock          = fields.Boolean('Can Request Restock / Withdraw', default=True)
    cap_edit_store       = fields.Boolean('Can Edit Store Page & Style', default=True)
    cap_request_payout   = fields.Boolean('Can Request Payout', default=True)
    cap_api              = fields.Boolean('Can Use Open API & Webhooks', default=True)
    cap_live             = fields.Boolean('Can Publish Shoppable Videos', default=True)
    cap_quick_sale       = fields.Boolean('Can Record Quick / Counter Sales', default=True)
    sla_hours            = fields.Integer('Fulfillment SLA (hours)', default=24,
        help='Target hours to confirm & ship an order before it is flagged overdue.')

    # ── Financial settlement ──────────────────────────────
    settlement_mode = fields.Selection([
        ('wallet',    'Wallet — accrue & periodic payout'),
        ('per_order', 'Per-order — settle each order instantly (no running dues)'),
        ('none',      'None — no financial tracking (house / owned stock)'),
    ], default='wallet', string='Settlement Mode',
        help='How money owed to the vendor is handled. Per-order settles every '
             'order on the spot so no balance/dues ever accrue. None disables '
             'commissions & wallet entirely.')
    settle_trigger = fields.Selection([
        ('confirm',  'On order confirmation'),
        ('deliver',  'On delivery'),
    ], default='confirm', string='Settle When',
        help='For per-order mode: when an order is marked settled.')
    hide_financials = fields.Boolean(
        'Hide Wallet & Dues from Vendor', default=False,
        help='Vendor sees no wallet balance, dues, or payable amounts.')

    @api.onchange('capability_preset')
    def _onchange_capability_preset(self):
        """Apply a quick capability profile. 'custom' leaves toggles untouched."""
        caps = ['cap_add_products', 'cap_edit_products', 'cap_archive_products',
                'cap_update_stock', 'cap_publish_products', 'cap_manage_price',
                'cap_flash_sale', 'cap_bundles', 'cap_join_promotions',
                'cap_import_products', 'cap_manage_orders', 'cap_cancel_orders',
                'cap_restock', 'cap_edit_store', 'cap_request_payout', 'cap_api',
                'cap_live', 'cap_quick_sale']
        p = self.capability_preset
        if p == 'full':
            for c in caps:
                self[c] = True
            self.settlement_mode = 'wallet'
            self.hide_financials = False
        elif p == 'managed':
            for c in caps:
                self[c] = True
            # managed = no destructive / financial self-service
            self.cap_archive_products = False
            self.cap_publish_products = False
            self.cap_manage_price = False
            self.cap_request_payout = False
        elif p == 'readonly':
            for c in caps:
                self[c] = False
        elif p == 'house':
            for c in caps:
                self[c] = False
            self.settlement_mode = 'none'
            self.hide_financials = True

    # ── Order settings ────────────────────────────────────
    sla_hours = fields.Integer('SLA Hours', default=24)
    sla_breach_action = fields.Selection([
        ('notify',       'Notify Vendor'),
        ('notify_admin', 'Notify + Admin'),
        ('transfer',     'Transfer to Uellow'),
        ('cancel',       'Cancel Order'),
    ], default='notify', string='SLA Breach Action')
    max_cancel_rate = fields.Float('Max Cancel Rate (%)', default=5.0)
    vendor_can_cancel = fields.Boolean('Vendor Can Cancel Orders', default=True)
    notify_admin_on_order = fields.Boolean('Notify Admin on Every Order', default=False)

    # ── Visibility settings ───────────────────────────────
    show_vendor_name = fields.Boolean('Show Vendor Name on Product', default=True)
    show_verification_badge = fields.Boolean('Show Verified Badge', default=True)
    show_ratings = fields.Boolean('Show Ratings', default=True)
    show_phone = fields.Boolean('Show Contact Phone', default=False)
    show_whatsapp = fields.Boolean('Show WhatsApp Button', default=False)

    sender_label = fields.Selection([
        ('uellow',  'Always Uellow'),
        ('vendor',  'Vendor Name'),
        ('both',    'Uellow by Vendor'),
    ], default='uellow', string='Shipping Sender Label')

    invoice_name = fields.Selection([
        ('uellow',  'Uellow W.L.L'),
        ('vendor',  'Vendor Name'),
        ('both',    'Both'),
    ], default='uellow', string='Invoice Name')

    # ── Communication settings ────────────────────────────
    vendor_sees_customer = fields.Boolean('Vendor Sees Customer Name/Phone', default=False)
    vendor_can_message = fields.Boolean('Vendor Can Message Customer', default=True)
    monitor_messages = fields.Boolean('Uellow Monitors Messages', default=True)

    # ── Shipping conditions ───────────────────────────────
    shipping_logic = fields.Selection([
        ('or',     'Any one condition (OR)'),
        ('and',    'All conditions must match (AND)'),
        ('custom', 'Custom'),
    ], default='or', string='Shipping Logic')

    cond_active_subscription = fields.Boolean('Active Subscription Required', default=True)
    cond_min_wallet = fields.Float('Minimum Wallet Balance', default=0.0)
    cond_wallet_enabled = fields.Boolean('Wallet Balance Condition', default=False)
    cond_online_only = fields.Boolean('Online Payment Only', default=False)
    cond_min_rating = fields.Float('Minimum Rating', default=0.0)
    cond_rating_enabled = fields.Boolean('Rating Condition', default=False)
    cond_max_cancel = fields.Float('Condition: Max Cancel Rate (%)', default=0.0)
    cond_cancel_enabled = fields.Boolean('Cancel Rate Condition', default=False)

    allow_cod = fields.Boolean('Allow Cash on Delivery', default=True)
    shipping_priority = fields.Selection([
        ('express', 'Express — 1 day'),
        ('standard','Standard — 2-3 days'),
        ('economy', 'Economy — 5-7 days'),
    ], default='standard', string='Shipping Priority')

    shipping_cost = fields.Selection([
        ('free',   'Free (included in plan)'),
        ('vendor', 'Vendor Pays'),
        ('uellow', 'Uellow Pays'),
    ], default='free', string='Shipping Cost')

    # ── Notifications ─────────────────────────────────────
    notify_new_order = fields.Boolean('Notify on New Order', default=True)
    notify_sla_warning = fields.Boolean('Notify on SLA Warning', default=True)
    notify_low_stock = fields.Boolean('Notify on Low Stock (< 5)', default=True)
    notify_weekly_report = fields.Boolean('Weekly Sales Report', default=True)
    notify_new_review = fields.Boolean('Notify on New Review', default=True)
    notify_subscription_expiry = fields.Boolean('Notify on Subscription Expiry', default=True)
    notify_dispute = fields.Boolean('Notify on Dispute', default=True)

    def get_style(self):
        """Resolve final colors: setting -> vendor.brand_color -> module default."""
        self.ensure_one()
        brand = self.vendor_id.brand_color or '#c0392b'
        return {
            'flash_bg': self.flash_bg_color or brand,
            'flash_accent': self.flash_accent_color or '#ffd60a',
            'section_title': self.section_title_color or brand,
            'price': self.price_color or '#1A7A6E',
            'badge': self.badge_color or '#c0392b',
            'header_text': self.header_text_color or '#ffffff',
        }
