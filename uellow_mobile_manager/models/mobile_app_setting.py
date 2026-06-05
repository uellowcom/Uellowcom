# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MobileAppSetting(models.Model):
    _name = 'mobile.app.setting'
    _description = 'Mobile App General Settings'
    _rec_name = 'website_id'

    website_id = fields.Many2one(
        'website', string='Website', required=True,
        default=lambda self: self.env['website'].search([], limit=1)
    )

    # App Info
    app_name = fields.Char(string='App Name', default='Uellow')
    app_logo = fields.Binary(string='App Logo', attachment=True)
    app_version_android = fields.Char(string='Min Android Version', default='1.0.0')
    app_version_ios = fields.Char(string='Min iOS Version', default='1.0.0')
    force_update = fields.Boolean(string='Force Update', default=False)
    maintenance_mode = fields.Boolean(string='Maintenance Mode', default=False)
    maintenance_message = fields.Text(string='Maintenance Message (EN)', default='We are under maintenance. Please try again later.')
    maintenance_message_en = fields.Text(string='Maintenance Message (EN — explicit)')
    maintenance_message_ar = fields.Text(string='Maintenance Message (AR)',
        default='نقوم بتحسينات على التطبيق. يُرجى المحاولة لاحقاً.')
    latest_version = fields.Char(string='Latest Released Version',
        help='Optional update prompt (non-blocking). Leave blank to disable.')
    release_notes_en = fields.Text(string='Release Notes (EN)')
    release_notes_ar = fields.Text(string='Release Notes (AR)')

    primary_color = fields.Char(string='Primary Color', default='#F5C320')
    dark_color    = fields.Char(string='Dark Color',    default='#412402')

    # Social Media Links
    whatsapp_number = fields.Char(string='WhatsApp Number', help='Include country code e.g. +96594709709')
    # ── Online-payment cashback (v2.1.21) ────────────────────────────
    online_cashback_enabled = fields.Boolean(
        string='Online Payment Cashback',
        help='When the customer pays ONLINE (KNET/card/…), credit a '
             'cashback to their wallet on payment capture. Cash orders '
             'get nothing — this nudges customers away from COD.')
    online_cashback_amount = fields.Float(
        string='Cashback Fixed Amount',
        help='Fixed amount (e.g. the cash-handling fee you save).')
    online_cashback_pct = fields.Float(
        string='Cashback % of Order', default=0.0,
        help='Extra percentage of the order total (0 = off). '
             'Total cashback = fixed + pct, capped below.')
    online_cashback_cap = fields.Float(
        string='Cashback Max per Order', default=0.0,
        help='Ceiling per order (0 = no cap).')
    online_cashback_min_order = fields.Float(
        string='Min Order for Cashback', default=0.0,
        help='Orders below this total earn nothing (0 = no minimum).')

    def cashback_for(self, total):
        """Resolve the cashback amount for an order total (0 if off)."""
        self.ensure_one()
        if not self.online_cashback_enabled:
            return 0.0
        if self.online_cashback_min_order and total < self.online_cashback_min_order:
            return 0.0
        amt = (self.online_cashback_amount or 0.0) + \
              total * (self.online_cashback_pct or 0.0) / 100.0
        if self.online_cashback_cap:
            amt = min(amt, self.online_cashback_cap)
        return round(max(amt, 0.0), 3)

    guest_checkout_enabled = fields.Boolean(
        string='Guest Checkout',
        help='Let guests place orders without an account (after a warning '
             'that they lose order tracking, loyalty points, etc.). '
             'Per-website like every app setting.')
    rank_badge_scope = fields.Selection([
        ('off', 'Off'),
        ('category', 'Category products only'),
        ('related', 'Related products only'),
        ('all', 'Everywhere'),
    ], string='Best-Seller Badge Placement', default='off',
        help='Where the quiet "Best seller in X" line (under the product '
             'name, no background) appears on app product cards.')
    facebook_url = fields.Char(string='Facebook URL')
    instagram_url = fields.Char(string='Instagram URL')
    youtube_url = fields.Char(string='YouTube URL')
    tiktok_url = fields.Char(string='TikTok URL')
    twitter_url = fields.Char(string='Twitter / X URL')

    # Contact & Support
    support_email = fields.Char(string='Support Email')
    support_phone = fields.Char(string='Support Phone')
    contact_url = fields.Char(string='Contact Page URL')
    about_us_url = fields.Char(string='About Us URL')
    privacy_policy_url = fields.Char(string='Privacy Policy URL')
    terms_url = fields.Char(string='Terms & Conditions URL')
    returns_url = fields.Char(string='Returns & Refunds URL')
    helpdesk_url = fields.Char(string='Customer Support / Helpdesk URL')
    blog_url = fields.Char(string='Blog URL')

    # Chat
    chat_enabled = fields.Boolean(string='Enable In-App Chat', default=True)
    chat_provider = fields.Selection([
        ('livechat', 'Odoo Live Chat'),
        ('whatsapp', 'WhatsApp'),
        ('custom', 'Custom URL'),
    ], string='Chat Provider', default='livechat')
    chat_custom_url = fields.Char(string='Custom Chat URL')

    # Google Play / App Store
    google_play_url = fields.Char(string='Google Play Store URL')
    app_store_url = fields.Char(string='Apple App Store URL')

    # FCM / Push
    fcm_server_key = fields.Char(string='FCM Server Key', groups='base.group_system')
    firebase_project_id = fields.Char(string='Firebase Project ID')

    # Theme
    primary_color = fields.Char(string='Primary Color', default='#FFC107')
    secondary_color = fields.Char(string='Secondary Color', default='#FF9800')
    accent_color = fields.Char(string='Accent Color', default='#FF5722')

    # Currency display
    currency_id = fields.Many2one('res.currency', string='Default Currency')

    # Countries for shipping
    country_ids = fields.Many2many('res.country', 'mobile_app_setting_country_rel', 'setting_id', 'country_id', string='Supported Countries')

    _sql_constraints = [
        ('website_unique', 'unique(website_id)', 'Settings already exist for this website.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Defensive: if the user (or an API path, or a stale browser
        session that bypassed `action_open_singleton`) tries to create a
        row for a website that already has one, transparently update the
        existing row instead of raising the Validation Error. This is
        what every caller actually wants — settings are a singleton per
        website."""
        default_wid = (self.env['website'].search([], limit=1).id) or False
        out = self.browse()
        to_create = []
        for vals in vals_list:
            wid = vals.get('website_id') or default_wid
            existing = self.search([('website_id', '=', wid)], limit=1) if wid else self.browse()
            if existing:
                # Drop website_id from write-vals; the row already has it
                # set, and changing it could collide elsewhere.
                write_vals = {k: v for k, v in vals.items() if k != 'website_id'}
                if write_vals:
                    existing.write(write_vals)
                out += existing
            else:
                to_create.append(vals)
        if to_create:
            out += super().create(to_create)
        return out

    @api.model
    def action_open_singleton(self):
        """Get-or-create the settings row for the default website and open
        its form. Used by the App Settings menu so admins never collide with
        the unique(website_id) constraint by creating an accidental duplicate
        when the row was already seeded by one of the API controllers."""
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return {
            'type':       'ir.actions.act_window',
            'name':       'App Settings',
            'res_model':  'mobile.app.setting',
            'view_mode':  'form',
            'res_id':     rec.id,
            'target':     'current',
        }


class ResPartnerDefaultAddress(models.Model):
    """v2.1.20 — primary (default) delivery address flag. Exactly one
    address per customer carries it; the app preselects it at checkout."""
    _inherit = 'res.partner'

    is_default_shipping = fields.Boolean('Default Delivery Address',
                                         default=False, index=True)
