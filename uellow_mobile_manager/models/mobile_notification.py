# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class MobileNotification(models.Model):
    _name = 'mobile.notification'
    _description = 'Mobile App Push Notification'
    _order = 'create_date desc'

    name = fields.Char(string='Notification Title', required=True)
    body = fields.Text(string='Message Body', required=True)
    image = fields.Binary(string='Notification Image', attachment=True)

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

    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1)
    )

    def action_send_now(self):
        """Mark as sent (actual FCM integration done via API)."""
        self.write({
            'state': 'sent',
            'sent_date': datetime.now(),
            'sent_count': 0,  # Will be updated by Flutter FCM service
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
