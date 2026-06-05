# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class MobileNotification(models.Model):
    _name = 'mobile.notification'
    _description = 'Mobile App Push Notification'
    _order = 'create_date desc'

    name = fields.Char(string='Notification Title', required=True)
    body = fields.Text(string='Message Body', required=True)
    # Bilingual broadcast — each recipient gets the text matching the
    # language THEIR app runs in (res.partner.push_lang, kept live by
    # register-device). Empty AR fields fall back to the EN text.
    name_ar = fields.Char(string='Title (Arabic)')
    body_ar = fields.Text(string='Body (Arabic)')
    image = fields.Binary(string='Notification Image', attachment=True)

    # Category drives delivery filtering — every user has a preference
    # toggle per category, so a customer who muted "promotions" never
    # receives a notification with category=promotion (see
    # mobile.notification.preference).
    category = fields.Selection([
        ('promotion',    'Promotion / Marketing'),
        ('order_update', 'Order Update'),
        ('general',      'General Info'),
        ('system',       'System / Critical'),
    ], string='Category', default='general', required=True,
        help='System notifications bypass user preferences (account/security only).')

    target_audience = fields.Selection([
        ('all', 'All Users'),
        ('specific', 'Specific Users'),
        ('segment', 'User Segment'),
    ], string='Target Audience', default='all', required=True)

    user_ids = fields.Many2many('res.users', 'mobile_notification_users_rel', 'notification_id', 'user_id', string='Specific Users')

    segment = fields.Selection([
        ('new_users', 'New Users (< 30 days)'),
        ('inactive', 'Inactive Users (> 30 days)'),
        ('buyers', 'Users Who Purchased'),
        ('no_purchase', 'Never Purchased'),
    ], string='User Segment')

    # Action on tap
    action_type = fields.Selection([
        ('none', 'Open App Home'),
        ('product', 'Open Product'),
        ('category', 'Open Category'),
        ('url', 'Open URL'),
        ('order', 'My Orders'),
    ], string='On Tap Action', default='none')

    product_id = fields.Many2one('product.template', string='Product')
    category_id = fields.Many2one('product.public.category', string='Category')
    action_url = fields.Char(string='URL')

    # Scheduling
    send_type = fields.Selection([
        ('now', 'Send Immediately'),
        ('scheduled', 'Schedule for Later'),
    ], string='Send Type', default='now')
    scheduled_date = fields.Datetime(string='Scheduled Date & Time')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', readonly=True)

    sent_count = fields.Integer(string='Sent To', readonly=True, default=0)
    sent_date = fields.Datetime(string='Sent On', readonly=True)

    # Per-customer read state for broadcasts (the app's "mark all read"
    # was a no-op for these — a broadcast has no single is_read flag).
    read_partner_ids = fields.Many2many(
        'res.partner', 'mobile_notification_read_rel',
        'notification_id', 'partner_id',
        string='Read By', copy=False)

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    def action_send_now(self):
        """v2.1.64 — really sends over FCM HTTP v1 to every registered
        device token (respecting each customer's category preference),
        then marks the record sent. Without Firebase creds it still
        lands in the in-app inbox as before."""
        sent = 0
        try:
            Engine = self.env['mobile.customer.notification']
            conf = self.env['mobile.notification.setting'].get_conf()
            Pref = self.env['mobile.notification.preference'].sudo()
            sessions = self.env['mobile.session'].sudo().search(
                [('fcm_token', '!=', False)])
            seen = set()
            for sess in sessions:
                tok = sess.fcm_token
                if not tok or tok in seen:
                    continue
                seen.add(tok)
                partner = getattr(sess, 'partner_id', None)
                if partner and self.category != 'system':
                    if not Pref.for_partner(partner).allows(self.category):
                        continue
                # Localize per recipient: partner.push_lang is the live
                # app language; guests fall back to the session's chosen
                # splash language. Default Arabic.
                lang = (getattr(partner, 'push_lang', '') if partner else '') \
                    or (sess.chosen_lang or '')
                en = (lang or 'ar').lower().startswith('en')
                title = (self.name if en else (self.name_ar or self.name))
                body = (self.body if en else (self.body_ar or self.body)) or ''
                if Engine.send_fcm(conf, tok, title, body):
                    sent += 1
        except Exception:
            pass
        self.write({
            'state': 'sent',
            'sent_date': datetime.now(),
            'sent_count': sent,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notification Sent',
                'message': 'Push notification has been queued for delivery.',
                'type': 'success',
            }
        }

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
