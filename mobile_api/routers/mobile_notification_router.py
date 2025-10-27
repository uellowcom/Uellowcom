# -*- coding: utf-8 -*-
"""Mobile Notification Router using Odoo models and Firebase"""

from typing import Annotated, List
import logging

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.base.models.res_partner import Partner

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..dependencies import get_current_user

try:
    from ..services.firebase_service import FirebaseService

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile/v1/notifications", tags=["Mobile Notifications"])


# Pydantic Models
class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_date: str
    data: dict = None


class PushTokenRequest(BaseModel):
    token: str
    device_type: str


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
):
    """Get user notifications"""
    try:
        domain = [("partner_id", "=", current_user.id)]
        if unread_only:
            domain.append(("is_read", "=", False))

        offset = (page - 1) * limit
        notifications = env["mobile.notification"].search(
            domain, limit=limit, offset=offset, order="create_date desc"
        )

        result = []
        for notification in notifications:
            result.append(
                NotificationResponse(
                    id=notification.id,
                    title=notification.title,
                    message=notification.message,
                    type=notification.notification_type,
                    is_read=notification.is_read,
                    created_date=notification.create_date.isoformat(),
                    data=notification.get_data_dict(),
                )
            )

        return result

    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")


@router.put("/{notification_id}/read")
async def mark_notification_read(
    env: Annotated[Environment, Depends(odoo_env)],
    notification_id: int,
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Mark notification as read"""
    try:
        notification = env["mobile.notification"].search(
            [("id", "=", notification_id), ("partner_id", "=", current_user.id)],
            limit=1,
        )

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.is_read = True
        notification.read_date = (
            env["mobile.notification"]._fields["read_date"].default()
        )

        return {"message": "Notification marked as read"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Mark all notifications as read"""
    try:
        notifications = env["mobile.notification"].search(
            [("partner_id", "=", current_user.id), ("is_read", "=", False)]
        )

        notifications.write(
            {
                "is_read": True,
                "read_date": env["mobile.notification"]._fields["read_date"].default(),
            }
        )

        return {"message": f"Marked {len(notifications)} notifications as read"}

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")


@router.post("/register-token")
async def register_push_token(
    env: Annotated[Environment, Depends(odoo_env)],
    token_data: PushTokenRequest,
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Register FCM push notification token"""
    try:
        # Update user's notification token
        current_user.mobile_notification_token = token_data.token

        # Update or create device record
        device = env["mobile.device"].search(
            [
                ("partner_id", "=", current_user.id),
                ("device_type", "=", token_data.device_type),
            ],
            limit=1,
        )

        if device:
            device.push_token = token_data.token
            device.is_active = True
        else:
            env["mobile.device"].create(
                {
                    "partner_id": current_user.id,
                    "device_id": f"token_{token_data.token[:10]}",
                    "device_type": token_data.device_type,
                    "push_token": token_data.token,
                    "is_active": True,
                }
            )

        return {"message": "Push token registered successfully"}

    except Exception as e:
        logger.error(f"Error registering push token: {e}")
        raise HTTPException(status_code=500, detail="Failed to register push token")


@router.post("/test-push")
async def send_test_notification(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Send test push notification"""
    try:
        if not current_user.mobile_notification_token:
            raise HTTPException(
                status_code=400, detail="No push token registered for this user"
            )

        # Create a notification record
        env["mobile.notification"].create(
            {
                "partner_id": current_user.id,
                "title": "Test Notification",
                "message": "This is a test notification from Yellow Mobile API",
                "notification_type": "system",
                "data": '{"type": "test"}',
            }
        )

        # Note: Firebase Cloud Messaging would be implemented here
        # For now, we just create the notification record
        return {
            "message": "Test notification created successfully",
            "note": "Firebase Cloud Messaging integration pending",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test notification")


@router.get("/unread-count")
async def get_unread_count(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Get count of unread notifications"""
    try:
        unread_count = env["mobile.notification"].search_count(
            [("partner_id", "=", current_user.id), ("is_read", "=", False)]
        )

        return {"unread_count": unread_count, "has_unread": unread_count > 0}

    except Exception as e:
        logger.error(f"Error fetching unread count: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unread count")


@router.delete("/{notification_id}")
async def delete_notification(
    env: Annotated[Environment, Depends(odoo_env)],
    notification_id: int,
    current_user: Annotated[Partner, Depends(get_current_user)],
):
    """Delete notification"""
    try:
        notification = env["mobile.notification"].search(
            [("id", "=", notification_id), ("partner_id", "=", current_user.id)],
            limit=1,
        )

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.unlink()

        return {"message": "Notification deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")
