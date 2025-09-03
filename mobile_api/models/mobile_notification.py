# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import logging

logger = logging.getLogger(__name__)


class MobileNotification(models.Model):
    _name = 'mobile.notification'
    _description = 'Mobile Notification'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Recipient', required=True, ondelete='cascade')
    title = fields.Char('Title', required=True)
    message = fields.Text('Message', required=True)
    notification_type = fields.Selection([
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('order', 'Order Update'),
        ('promotion', 'Promotion'),
        ('wallet', 'Wallet Transaction'),
        ('system', 'System Notification'),
    ], string='Type', default='info', required=True)
    
    is_read = fields.Boolean('Is Read', default=False)
    read_date = fields.Datetime('Read Date')
    
    # Additional data as JSON
    data = fields.Text('Additional Data')
    
    # Push notification tracking
    push_sent = fields.Boolean('Push Sent', default=False)
    push_sent_date = fields.Datetime('Push Sent Date')
    push_error = fields.Text('Push Error')

    def get_data_dict(self):
        """Get additional data as dictionary"""
        self.ensure_one()
        try:
            return json.loads(self.data or '{}')
        except:
            return {}

    def set_data_dict(self, data_dict):
        """Set additional data from dictionary"""
        self.ensure_one()
        self.data = json.dumps(data_dict)

    @api.model
    def create_notification(self, partner_id, title, message, notification_type='info', data=None, send_push=True):
        """Create a new notification"""
        notification = self.create({
            'partner_id': partner_id,
            'title': title,
            'message': message,
            'notification_type': notification_type,
            'data': json.dumps(data or {}),
        })
        
        if send_push:
            notification._send_push_notification()
        
        return notification

    def _send_push_notification(self):
        """Send push notification via Firebase"""
        self.ensure_one()
        
        try:
            partner = self.partner_id
            if not partner.mobile_notification_token:
                logger.info(f"No push token for partner {partner.id}")
                return False

            from ..services.firebase_service import FirebaseMessagingService
            firebase_messaging = FirebaseMessagingService()
            
            # Prepare notification data
            data = self.get_data_dict()
            data.update({
                'notification_id': str(self.id),
                'type': self.notification_type,
                'timestamp': self.create_date.isoformat(),
            })

            # Send push notification
            success = firebase_messaging.send_notification(
                token=partner.mobile_notification_token,
                title=self.title,
                body=self.message,
                data=data
            )

            # Update notification record
            self.write({
                'push_sent': success,
                'push_sent_date': fields.Datetime.now() if success else False,
                'push_error': None if success else 'Failed to send push notification'
            })

            return success

        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            self.write({
                'push_sent': False,
                'push_error': str(e)
            })
            return False

    @api.model
    def notify_order_update(self, partner_id, order_id, status, message=None):
        """Create order update notification"""
        order = self.env['sale.order'].browse(order_id)
        if not order.exists():
            return False

        title = f"Order Update - {order.name}"
        if not message:
            message = f"Your order status has been updated to: {status}"

        return self.create_notification(
            partner_id=partner_id,
            title=title,
            message=message,
            notification_type='order',
            data={
                'order_id': order_id,
                'order_name': order.name,
                'status': status,
                'action': 'view_order'
            }
        )

    @api.model
    def notify_wallet_transaction(self, partner_id, transaction_id, amount, transaction_type):
        """Create wallet transaction notification"""
        partner = self.env['res.partner'].browse(partner_id)
        
        if transaction_type == 'credit':
            title = "Wallet Credited"
            message = f"Your wallet has been credited with {abs(amount)} {partner.company_id.currency_id.symbol}"
        else:
            title = "Wallet Debited"
            message = f"Your wallet has been debited with {abs(amount)} {partner.company_id.currency_id.symbol}"

        return self.create_notification(
            partner_id=partner_id,
            title=title,
            message=message,
            notification_type='wallet',
            data={
                'transaction_id': transaction_id,
                'amount': amount,
                'type': transaction_type,
                'action': 'view_wallet'
            }
        )

    @api.model
    def notify_promotion(self, partner_ids, title, message, promotion_data=None):
        """Send promotion notification to multiple users"""
        notifications = []
        for partner_id in partner_ids:
            notification = self.create_notification(
                partner_id=partner_id,
                title=title,
                message=message,
                notification_type='promotion',
                data=promotion_data or {}
            )
            notifications.append(notification)
        
        return notifications

    @api.model
    def send_bulk_notification(self, partner_ids, title, message, notification_type='info', data=None):
        """Send notification to multiple users"""
        notifications = []
        for partner_id in partner_ids:
            notification = self.create_notification(
                partner_id=partner_id,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data
            )
            notifications.append(notification)
        
        return notifications

    def mark_as_read(self):
        """Mark notification as read"""
        self.ensure_one()
        self.write({
            'is_read': True,
            'read_date': fields.Datetime.now()
        })

    @api.model
    def cleanup_old_notifications(self, days=30):
        """Clean up old notifications"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_notifications = self.search([
            ('create_date', '<', cutoff_date),
            ('is_read', '=', True)
        ])
        
        count = len(old_notifications)
        old_notifications.unlink()
        
        logger.info(f"Cleaned up {count} old notifications")
        return count


class ResPartnerNotification(models.Model):
    _inherit = 'res.partner'

    notification_ids = fields.One2many('mobile.notification', 'partner_id', string='Notifications')
    unread_notification_count = fields.Integer('Unread Notifications', compute='_compute_unread_notifications')

    def _compute_unread_notifications(self):
        """Compute unread notification count"""
        for partner in self:
            partner.unread_notification_count = self.env['mobile.notification'].search_count([
                ('partner_id', '=', partner.id),
                ('is_read', '=', False)
            ])

    def send_notification(self, title, message, notification_type='info', data=None, send_push=True):
        """Send notification to this partner"""
        self.ensure_one()
        return self.env['mobile.notification'].create_notification(
            partner_id=self.id,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data,
            send_push=send_push
        )
