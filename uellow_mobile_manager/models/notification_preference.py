# -*- coding: utf-8 -*-
"""
Per-customer notification preferences.

One row per partner. Drives the filter in
mobile.notification._eligible_partners(): a notification with
category='promotion' is dropped for partners with
receive_promotions=False, etc. System-category notifications bypass
preferences entirely (account/security warnings always reach the user).

The Flutter app reads/writes this through:
  GET  /api/mobile/v2/notifications/preferences
  POST /api/mobile/v2/notifications/preferences/save
"""
from odoo import models, fields, api


class MobileNotificationPreference(models.Model):
    _name = 'mobile.notification.preference'
    _description = 'Customer Notification Preferences'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade',
        index=True)
    push_enabled = fields.Boolean(
        string='Push Notifications Enabled', default=True,
        help='Master switch — when off, no push is delivered regardless of category.')
    receive_promotions = fields.Boolean(
        string='Promotions & Marketing', default=True,
        help='Discounts, flash sales, new arrivals, vendor offers.')
    receive_order_updates = fields.Boolean(
        string='Order Updates', default=True,
        help='Order placed, confirmed, shipped, out for delivery, delivered.')
    receive_general = fields.Boolean(
        string='General News', default=True,
        help='App tips, loyalty milestones, policy updates.')

    _sql_constraints = [
        ('uniq_partner', 'unique(partner_id)',
         'Each customer can only have one notification preference row.'),
    ]

    @api.model
    def for_partner(self, partner):
        """Get or create the preferences row for a partner."""
        if not partner:
            return self.browse()
        rec = self.sudo().search([('partner_id', '=', partner.id)], limit=1)
        if not rec:
            rec = self.sudo().create({'partner_id': partner.id})
        return rec

    def allows(self, category):
        """Return True if THIS preference row allows the given category."""
        self.ensure_one()
        if category == 'system':
            return True
        if not self.push_enabled:
            return False
        return {
            'promotion':    self.receive_promotions,
            'order_update': self.receive_order_updates,
            'general':      self.receive_general,
        }.get(category, True)
