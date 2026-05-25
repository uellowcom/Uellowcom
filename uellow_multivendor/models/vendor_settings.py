from odoo import models, fields, api, _


class VendorSettings(models.Model):
    """
    Per-vendor settings — intervention level, visibility, shipping rules.
    One settings record per vendor, auto-created on approval.
    """
    _name = 'uellow.vendor.settings'
    _description = 'Vendor Settings'
    _rec_name = 'vendor_id'

    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )

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
