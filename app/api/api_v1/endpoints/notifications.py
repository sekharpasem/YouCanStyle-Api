from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Dict, Any, Optional
from app.core.auth import get_current_user
from app.schemas.notification import NotificationResponse, NotificationSettings
from app.services.notification_service import (
    get_notifications, mark_notification_read, mark_all_notifications_read,
    delete_notification, get_unread_notification_count, register_device_token,
    remove_device_token, get_or_create_notification_settings, update_notification_settings
)

router = APIRouter()

@router.get("/", response_model=List[NotificationResponse])
async def get_user_notifications(
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get notifications for the current user
    """
    notifications = await get_notifications(
        str(current_user["_id"]),
        unread_only=unread_only,
        skip=skip,
        limit=limit
    )
    
    return notifications

@router.get("/count", response_model=Dict[str, int])
async def get_notification_count(current_user: dict = Depends(get_current_user)):
    """
    Get unread notification count for the current user
    """
    count = await get_unread_notification_count(str(current_user["_id"]))
    return {"count": count}

@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark a notification as read
    """
    notification = await mark_notification_read(notification_id, str(current_user["_id"]))
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return notification

@router.put("/read-all", response_model=Dict[str, int])
async def mark_all_as_read(current_user: dict = Depends(get_current_user)):
    """
    Mark all notifications as read
    """
    count = await mark_all_notifications_read(str(current_user["_id"]))
    return {"count": count}

@router.delete("/{notification_id}", response_model=Dict[str, bool])
async def delete_user_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a notification
    """
    success = await delete_notification(notification_id, str(current_user["_id"]))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"success": success}

@router.post("/device-token", response_model=Dict[str, str])
async def register_push_token(
    device_token: str = Body(..., embed=True),
    device_type: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Register device token for push notifications
    """
    # Validate device type
    if device_type not in ["ios", "android", "web"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device type. Must be 'ios', 'android', or 'web'"
        )
    
    token = await register_device_token(
        str(current_user["_id"]),
        device_token,
        device_type
    )
    
    return {"status": "success", "id": token["id"]}

@router.delete("/device-token", response_model=Dict[str, bool])
async def remove_push_token(
    device_token: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove device token for push notifications
    """
    success = await remove_device_token(device_token)
    return {"success": success}

@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    """
    Get notification settings for the current user
    """
    settings = await get_or_create_notification_settings(str(current_user["_id"]))
    return settings

@router.put("/settings", response_model=NotificationSettings)
async def update_user_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(get_current_user)
):
    """
    Update notification settings for the current user
    """
    updated_settings = await update_notification_settings(
        str(current_user["_id"]),
        settings.dict()
    )
    
    return updated_settings
