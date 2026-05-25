# -*- coding: utf-8 -*-
from odoo import models, fields


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
    maintenance_message = fields.Text(string='Maintenance Message', default='We are under maintenance. Please try again later.')

    # Social Media Links
    whatsapp_number = fields.Char(string='WhatsApp Number', help='Include country code e.g. +96594709709')
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
