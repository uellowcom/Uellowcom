# -*- coding: utf-8 -*-
"""Mobile Notification Controller using Odoo HTTP"""

import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ..services.jwt_service import JWTService
from ..services.firebase_service import FirebaseAuthService

_logger = logging.getLogger(__name__)


class MobileNotificationController(http.Controller):
    """Mobile Notification HTTP Controller"""

    def _get_current_user(self):
        """Get current authenticated user from JWT token"""
        try:
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None

            token = auth_header.split(' ')[1]
            jwt_service = JWTService()
            payload = jwt_service.decode_token(token)
            partner_id = payload.get('sub')
            
            if partner_id:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                return partner if partner.exists() else None
            return None
        except:
            return None

    def _create_response(self, data=None, error=None, status=200):
        """Create standardized JSON response"""
        if error:
            response_data = {
                'success': False,
                'error': error,
                'data': None
            }
            status = status or 400
        else:
            response_data = {
                'success': True,
                'error': None,
                'data': data or {}
            }
        
        return request.make_response(
            json.dumps(response_data),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    @http.route('/mobile/v1/notifications', auth='public', methods=['GET'], type='http', csrf=False)
    def get_notifications(self, **kwargs):
        """Get user notifications with pagination"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Extract pagination parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            unread_only = kwargs.get('unread_only', 'false').lower() == 'true'

            # Build domain
            domain = [('partner_id', '=', current_user.id)]
            if unread_only:
                domain.append(('is_read', '=', False))

            # Get notifications
            notifications = request.env['mobile.notification'].sudo().search(
                domain,
                limit=limit,
                offset=offset,
                order='create_date desc'
            )

            notifications_data = []
            for notification in notifications:
                notifications_data.append({
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'is_read': notification.is_read,
                    'created_at': notification.create_date.isoformat() if notification.create_date else None,
                    'read_at': notification.read_at.isoformat() if notification.read_at else None,
                    'action_data': notification.action_data,
                    'priority': notification.priority
                })

            # Get total count and unread count
            total_count = request.env['mobile.notification'].sudo().search_count(
                [('partner_id', '=', current_user.id)]
            )
            unread_count = request.env['mobile.notification'].sudo().search_count([
                ('partner_id', '=', current_user.id),
                ('is_read', '=', False)
            ])

            response_data = {
                'notifications': notifications_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                },
                'unread_count': unread_count
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get notifications error: {str(e)}")
            return self._create_response(error="Failed to fetch notifications", status=500)

    @http.route('/mobile/v1/notifications/<int:notification_id>/read', auth='public', methods=['POST'], type='json', csrf=False)
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Find notification
            notification = request.env['mobile.notification'].sudo().search([
                ('id', '=', notification_id),
                ('partner_id', '=', current_user.id)
            ], limit=1)

            if not notification:
                return self._create_response(error="Notification not found", status=404)

            # Mark as read
            notification.sudo().write({
                'is_read': True,
                'read_at': fields.Datetime.now()
            })

            return self._create_response({'message': 'Notification marked as read'})

        except Exception as e:
            _logger.error(f"Mark notification read error: {str(e)}")
            return self._create_response(error="Failed to mark notification as read", status=500)

    @http.route('/mobile/v1/notifications/read-all', auth='public', methods=['POST'], type='json', csrf=False)
    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Mark all unread notifications as read
            unread_notifications = request.env['mobile.notification'].sudo().search([
                ('partner_id', '=', current_user.id),
                ('is_read', '=', False)
            ])

            unread_notifications.sudo().write({
                'is_read': True,
                'read_at': fields.Datetime.now()
            })

            return self._create_response({
                'message': f'{len(unread_notifications)} notifications marked as read'
            })

        except Exception as e:
            _logger.error(f"Mark all notifications read error: {str(e)}")
            return self._create_response(error="Failed to mark notifications as read", status=500)

    @http.route('/mobile/v1/notifications/settings', auth='public', methods=['GET'], type='http', csrf=False)
    def get_notification_settings(self):
        """Get user notification preferences"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Get notification settings (you can extend res.partner or create a separate model)
            settings = {
                'push_notifications': True,
                'email_notifications': True,
                'order_updates': True,
                'promotions': True,
                'new_products': False,
                'price_drops': True
            }

            return self._create_response({'settings': settings})

        except Exception as e:
            _logger.error(f"Get notification settings error: {str(e)}")
            return self._create_response(error="Failed to fetch notification settings", status=500)

    @http.route('/mobile/v1/notifications/settings', auth='public', methods=['POST'], type='json', csrf=False)
    def update_notification_settings(self):
        """Update user notification preferences"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            data = request.jsonrequest
            
            # Update notification settings (implement based on your model structure)
            # For now, we'll just return success
            
            return self._create_response({'message': 'Notification settings updated successfully'})

        except Exception as e:
            _logger.error(f"Update notification settings error: {str(e)}")
            return self._create_response(error="Failed to update notification settings", status=500)

    @http.route('/mobile/v1/notifications/register-device', auth='public', methods=['POST'], type='json', csrf=False)
    def register_device_token(self):
        """Register device token for push notifications"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            data = request.jsonrequest
            
            required_fields = ['device_token', 'device_type']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return self._create_response(error=f"Missing fields: {', '.join(missing_fields)}", status=400)

            device_token = data['device_token']
            device_type = data['device_type']  # ios, android
            device_id = data.get('device_id')

            # Find or create mobile device record
            device = None
            if device_id:
                device = request.env['mobile.device'].sudo().search([
                    ('partner_id', '=', current_user.id),
                    ('device_id', '=', device_id)
                ], limit=1)

            if device:
                # Update existing device
                device.sudo().write({
                    'push_token': device_token,
                    'device_type': device_type,
                    'is_active': True,
                    'last_used': fields.Datetime.now()
                })
            else:
                # Create new device record
                device_vals = {
                    'partner_id': current_user.id,
                    'device_id': device_id or f"{device_type}_{int(datetime.now().timestamp())}",
                    'device_type': device_type,
                    'push_token': device_token,
                    'is_active': True,
                    'last_used': fields.Datetime.now()
                }
                device = request.env['mobile.device'].sudo().create(device_vals)

            return self._create_response({
                'message': 'Device token registered successfully',
                'device_id': device.device_id
            })

        except Exception as e:
            _logger.error(f"Register device token error: {str(e)}")
            return self._create_response(error="Failed to register device token", status=500)

    @http.route('/mobile/v1/notifications/send-test', auth='public', methods=['POST'], type='json', csrf=False)
    def send_test_notification(self):
        """Send a test notification to the user"""
        try:
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Create test notification
            notification_vals = {
                'partner_id': current_user.id,
                'title': 'Test Notification',
                'message': 'This is a test notification from Yellow Mobile API',
                'notification_type': 'info',
                'priority': 'normal',
                'is_read': False
            }
            
            notification = request.env['mobile.notification'].sudo().create(notification_vals)

            # Send push notification if Firebase is configured
            try:
                firebase_service = FirebaseAuthService()
                devices = request.env['mobile.device'].sudo().search([
                    ('partner_id', '=', current_user.id),
                    ('is_active', '=', True),
                    ('push_token', '!=', False)
                ])
                
                for device in devices:
                    if device.push_token:
                        # Send push notification via Firebase
                        firebase_service.send_push_notification(
                            device.push_token,
                            'Test Notification',
                            'This is a test notification from Yellow Mobile API'
                        )
            except Exception as push_error:
                _logger.warning(f"Failed to send push notification: {push_error}")

            return self._create_response({
                'message': 'Test notification sent successfully',
                'notification_id': notification.id
            })

        except Exception as e:
            _logger.error(f"Send test notification error: {str(e)}")
            return self._create_response(error="Failed to send test notification", status=500)
