# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any, List, Optional
from datetime import datetime

from odoo.api import Environment

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from ..dependencies import odoo_env, get_current_user

# Define the router
router = APIRouter(prefix="/mobile/v1/notifications", tags=["notifications"])

# Models for response
class Notification(BaseModel):
    id: int
    title: str
    message: str
    date: datetime
    is_read: bool
    notification_type: str
    data: Optional[Dict[str, Any]] = None

class ApiResponse(BaseModel):
    success: bool = True
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.get("", response_model=ApiResponse)
async def get_notifications(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False)
):
    """Get user notifications with pagination and filtering"""
    try:
        # Get partner from current user
        partner_id = current_user.get('partner_id')
        if not partner_id:
            return {
                'success': False,
                'error': 'User has no associated partner'
            }
        
        # Check if mail.notification model exists
        if 'mail.notification' not in env:
            return {
                'success': True,
                'data': {
                    'notifications': [],
                    'unread_count': 0,
                    'total_count': 0
                }
            }
        
        # Build domain for notifications
        domain = [('res_partner_id', '=', partner_id)]
        if unread_only:
            domain.append(('is_read', '=', False))
        
        # Count total and unread notifications
        total_count = env['mail.notification'].sudo().search_count(domain)
        unread_count = env['mail.notification'].sudo().search_count(
            [('res_partner_id', '=', partner_id), ('is_read', '=', False)]
        )
        
        # Get notifications with pagination
        notifications_records = env['mail.notification'].sudo().search(
            domain, limit=limit, offset=offset, order='date desc'
        )
        
        notifications = []
        for notif in notifications_records:
            # Get related message
            message = notif.mail_message_id
            
            # Extract notification data
            notification_data = {
                'id': notif.id,
                'title': message.subject or 'Notification',
                'message': message.body,
                'date': notif.date or datetime.now(),
                'is_read': notif.is_read,
                'notification_type': message.message_type or 'notification',
                'data': {}
            }
            
            # Add reference data if available
            if message.model and message.res_id:
                notification_data['data']['reference'] = {
                    'model': message.model,
                    'id': message.res_id
                }
            
            notifications.append(notification_data)
        
        return {
            'success': True,
            'data': {
                'notifications': notifications,
                'unread_count': unread_count,
                'total_count': total_count
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/mark-read/{notification_id}", response_model=ApiResponse)
async def mark_notification_read(
    notification_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)]
):
    """Mark a notification as read"""
    try:
        # Get partner from current user
        partner_id = current_user.get('partner_id')
        if not partner_id:
            return {
                'success': False,
                'error': 'User has no associated partner'
            }
        
        # Check if mail.notification model exists
        if 'mail.notification' not in env:
            return {
                'success': False,
                'error': 'Notification system not available'
            }
        
        # Get the notification
        notification = env['mail.notification'].sudo().search([
            ('id', '=', notification_id),
            ('res_partner_id', '=', partner_id)
        ])
        
        if not notification:
            return {
                'success': False,
                'error': 'Notification not found or not accessible'
            }
        
        # Mark as read
        notification.sudo().write({'is_read': True})
        
        return {
            'success': True,
            'data': {
                'message': 'Notification marked as read'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/mark-all-read", response_model=ApiResponse)
async def mark_all_notifications_read(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)]
):
    """Mark all notifications as read"""
    try:
        # Get partner from current user
        partner_id = current_user.get('partner_id')
        if not partner_id:
            return {
                'success': False,
                'error': 'User has no associated partner'
            }
        
        # Check if mail.notification model exists
        if 'mail.notification' not in env:
            return {
                'success': False,
                'error': 'Notification system not available'
            }
        
        # Get all unread notifications
        notifications = env['mail.notification'].sudo().search([
            ('res_partner_id', '=', partner_id),
            ('is_read', '=', False)
        ])
        
        # Mark all as read
        if notifications:
            notifications.sudo().write({'is_read': True})
        
        return {
            'success': True,
            'data': {
                'message': f'{len(notifications)} notifications marked as read'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/register-device", response_model=ApiResponse)
async def register_device(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    device_token: str,
    device_type: str = Query(..., regex='^(ios|android)$')
):
    """Register a device for push notifications"""
    try:
        # Get mobile user from current user
        mobile_user_id = current_user.get('id')
        if not mobile_user_id:
            return {
                'success': False,
                'error': 'Invalid user'
            }
        
        # Check if mobile.device model exists
        if 'mobile.device' not in env:
            return {
                'success': False,
                'error': 'Device registration not available'
            }
        
        # Check if device already exists
        existing_device = env['mobile.device'].sudo().search([
            ('device_token', '=', device_token),
            ('mobile_user_id', '=', mobile_user_id)
        ], limit=1)
        
        if existing_device:
            # Update existing device
            existing_device.sudo().write({
                'device_type': device_type,
                'is_active': True,
                'last_activity': datetime.now()
            })
            device_id = existing_device.id
        else:
            # Create new device
            device = env['mobile.device'].sudo().create({
                'mobile_user_id': mobile_user_id,
                'device_token': device_token,
                'device_type': device_type,
                'is_active': True,
                'last_activity': datetime.now()
            })
            device_id = device.id
        
        return {
            'success': True,
            'data': {
                'device_id': device_id,
                'message': 'Device registered successfully'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/unregister-device", response_model=ApiResponse)
async def unregister_device(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
    device_token: str
):
    """Unregister a device from push notifications"""
    try:
        # Get mobile user from current user
        mobile_user_id = current_user.get('id')
        if not mobile_user_id:
            return {
                'success': False,
                'error': 'Invalid user'
            }
        
        # Check if mobile.device model exists
        if 'mobile.device' not in env:
            return {
                'success': False,
                'error': 'Device registration not available'
            }
        
        # Find the device
        device = env['mobile.device'].sudo().search([
            ('device_token', '=', device_token),
            ('mobile_user_id', '=', mobile_user_id)
        ], limit=1)
        
        if not device:
            return {
                'success': False,
                'error': 'Device not found'
            }
        
        # Deactivate the device
        device.sudo().write({
            'is_active': False
        })
        
        return {
            'success': True,
            'data': {
                'message': 'Device unregistered successfully'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
