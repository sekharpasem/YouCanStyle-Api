from typing import Dict, Any, List, Optional
from app.db.mongodb import db
from app.schemas.notification import NotificationType, NotificationCreate, NotificationUpdate
from datetime import datetime
from bson import ObjectId
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock FCM client (in production, use firebase-admin SDK)
class MockFCMClient:
    async def send_message(self, token, data):
        logger.info(f"Sending push notification to {token}: {json.dumps(data)}")
        return {"success": True, "message_id": "mock-id"}

fcm_client = MockFCMClient()

async def create_notification(notification: NotificationCreate) -> Dict[str, Any]:
    """
    Create a new notification
    """
    # Create notification data
    notification_data = notification.dict()
    notification_data["read"] = False
    notification_data["createdAt"] = datetime.utcnow()
    
    # Insert notification into database
    result = await db.db.notifications.insert_one(notification_data)
    
    # Get the created notification
    created_notification = await db.db.notifications.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_notification["id"] = str(created_notification["_id"])
    
    # Try to send push notification
    await send_push_notification(notification.userId, created_notification)
    
    return created_notification

async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get notifications for a user
    """
    # Build query
    query = {"userId": user_id}
    
    if unread_only:
        query["read"] = False
    
    # Execute query
    cursor = db.db.notifications.find(query).skip(skip).limit(limit).sort("createdAt", -1)
    notifications = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for notification in notifications:
        notification["id"] = str(notification["_id"])
    
    return notifications

async def mark_notification_read(notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Mark a notification as read
    """
    # Update notification
    await db.db.notifications.update_one(
        {"_id": ObjectId(notification_id), "userId": user_id},
        {"$set": {"read": True, "readAt": datetime.utcnow()}}
    )
    
    # Get the updated notification
    updated_notification = await db.db.notifications.find_one({"_id": ObjectId(notification_id)})
    
    if updated_notification:
        updated_notification["id"] = str(updated_notification["_id"])
    
    return updated_notification

async def mark_all_notifications_read(user_id: str) -> int:
    """
    Mark all notifications as read for a user
    """
    result = await db.db.notifications.update_many(
        {"userId": user_id, "read": False},
        {"$set": {"read": True, "readAt": datetime.utcnow()}}
    )
    
    return result.modified_count

async def delete_notification(notification_id: str, user_id: str) -> bool:
    """
    Delete a notification
    """
    result = await db.db.notifications.delete_one(
        {"_id": ObjectId(notification_id), "userId": user_id}
    )
    
    return result.deleted_count > 0

async def get_unread_notification_count(user_id: str) -> int:
    """
    Get unread notification count for a user
    """
    count = await db.db.notifications.count_documents({"userId": user_id, "read": False})
    return count

async def register_device_token(user_id: str, device_token: str, device_type: str) -> Dict[str, Any]:
    """
    Register a device token for push notifications
    """
    # Check if token already exists
    existing_token = await db.db.push_tokens.find_one({"deviceToken": device_token})
    
    if existing_token:
        # Update user ID if needed
        if existing_token["userId"] != user_id:
            await db.db.push_tokens.update_one(
                {"deviceToken": device_token},
                {"$set": {"userId": user_id, "updatedAt": datetime.utcnow()}}
            )
        
        existing_token["id"] = str(existing_token["_id"])
        return existing_token
    
    # Create new token registration
    token_data = {
        "userId": user_id,
        "deviceToken": device_token,
        "deviceType": device_type,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.db.push_tokens.insert_one(token_data)
    
    # Get the created token
    created_token = await db.db.push_tokens.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_token["id"] = str(created_token["_id"])
    
    return created_token

async def remove_device_token(device_token: str) -> bool:
    """
    Remove a device token
    """
    result = await db.db.push_tokens.delete_one({"deviceToken": device_token})
    return result.deleted_count > 0

async def get_user_device_tokens(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all device tokens for a user
    """
    cursor = db.db.push_tokens.find({"userId": user_id})
    tokens = await cursor.to_list(length=100)
    
    # Transform _id field to string
    for token in tokens:
        token["id"] = str(token["_id"])
    
    return tokens

async def send_push_notification(user_id: str, notification_data: Dict[str, Any]) -> bool:
    """
    Send push notification to all user devices
    """
    try:
        # Get user settings
        user_settings = await db.db.notification_settings.find_one({"userId": user_id})
        
        # If user has disabled push notifications, return
        if user_settings and not user_settings.get("push", True):
            return False
            
        # Check notification type and user preferences
        notification_type = notification_data.get("type")
        if notification_type:
            if notification_type.startswith("booking_") and user_settings and not user_settings.get("bookingUpdates", True):
                return False
            if notification_type == "chat_message" and user_settings and not user_settings.get("chatMessages", True):
                return False
        
        # Get user device tokens
        tokens = await get_user_device_tokens(user_id)
        
        if not tokens:
            return False
            
        success = False
        
        # Format push notification payload
        payload = {
            "notification": {
                "title": notification_data["title"],
                "body": notification_data["message"],
            },
            "data": {
                "type": notification_data.get("type", ""),
                "id": notification_data.get("id", ""),
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
            }
        }
        
        # Add additional data if present
        if notification_data.get("data"):
            payload["data"].update(notification_data["data"])
        
        # Send to all devices
        for token in tokens:
            try:
                # In production, this would use the Firebase Admin SDK
                # Here, we're just logging the notification
                result = await fcm_client.send_message(token["deviceToken"], payload)
                
                if result.get("success"):
                    success = True
                    
            except Exception as e:
                logger.error(f"Error sending push notification: {str(e)}")
                
                # If the token is invalid, remove it
                if "invalid" in str(e).lower() or "not registered" in str(e).lower():
                    await remove_device_token(token["deviceToken"])
        
        return success
        
    except Exception as e:
        logger.error(f"Error in send_push_notification: {str(e)}")
        return False

async def get_or_create_notification_settings(user_id: str) -> Dict[str, Any]:
    """
    Get or create notification settings for a user
    """
    settings = await db.db.notification_settings.find_one({"userId": user_id})
    
    if settings:
        settings["id"] = str(settings["_id"])
        return settings
        
    # Create default settings
    default_settings = {
        "userId": user_id,
        "bookingUpdates": True,
        "chatMessages": True,
        "promotions": True,
        "reminders": True,
        "email": True,
        "push": True,
        "createdAt": datetime.utcnow()
    }
    
    result = await db.db.notification_settings.insert_one(default_settings)
    
    # Get the created settings
    created_settings = await db.db.notification_settings.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_settings["id"] = str(created_settings["_id"])
    
    return created_settings

async def update_notification_settings(user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update notification settings for a user
    """
    # Get current settings or create default ones
    current_settings = await get_or_create_notification_settings(user_id)
    
    # Update settings
    update_data = {k: v for k, v in settings.items() if k in [
        "bookingUpdates", "chatMessages", "promotions", "reminders", "email", "push"
    ]}
    
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        
        await db.db.notification_settings.update_one(
            {"userId": user_id},
            {"$set": update_data}
        )
    
    # Get the updated settings
    updated_settings = await db.db.notification_settings.find_one({"userId": user_id})
    
    # Transform the _id field to string
    updated_settings["id"] = str(updated_settings["_id"])
    
    return updated_settings

async def send_booking_notification(booking_data: Dict[str, Any], notification_type: NotificationType) -> Dict[str, Any]:
    """
    Send a notification about a booking event
    """
    # Determine recipient based on notification type
    # For booking events, both client and stylist get notified
    recipients = [booking_data["clientId"], booking_data["stylistId"]]
    created_notifications = []
    
    for recipient_id in recipients:
        title = ""
        message = ""
        
        # Determine title and message based on type and recipient
        if notification_type == NotificationType.BOOKING_CREATED:
            if recipient_id == booking_data["stylistId"]:
                title = "New Booking Request"
                message = f"You have a new booking request from {booking_data.get('clientName', 'a client')}."
            else:
                title = "Booking Created"
                message = "Your booking request has been submitted."
                
        elif notification_type == NotificationType.BOOKING_CONFIRMED:
            if recipient_id == booking_data["stylistId"]:
                title = "Booking Confirmed"
                message = f"Your booking with {booking_data.get('clientName', 'a client')} has been confirmed."
            else:
                title = "Booking Confirmed"
                message = "Your booking request has been confirmed by the stylist."
                
        elif notification_type == NotificationType.BOOKING_CANCELLED:
            if recipient_id == booking_data["stylistId"]:
                title = "Booking Cancelled"
                message = f"A booking with {booking_data.get('clientName', 'a client')} has been cancelled."
            else:
                title = "Booking Cancelled"
                message = "Your booking has been cancelled."
                
        elif notification_type == NotificationType.BOOKING_COMPLETED:
            if recipient_id == booking_data["stylistId"]:
                title = "Booking Completed"
                message = f"Your session with {booking_data.get('clientName', 'a client')} has been completed."
            else:
                title = "Booking Completed"
                message = "Your styling session has been completed. Please leave a review!"
                
        elif notification_type == NotificationType.BOOKING_REMINDER:
            title = "Upcoming Booking"
            message = f"Reminder: You have a booking scheduled for {booking_data.get('date', 'soon')}."
        
        # Create notification
        notification = NotificationCreate(
            userId=recipient_id,
            type=notification_type,
            title=title,
            message=message,
            data={
                "bookingId": booking_data.get("id", str(booking_data.get("_id", ""))),
                "bookingDate": booking_data.get("date", "").isoformat() if isinstance(booking_data.get("date"), datetime) else booking_data.get("date", "")
            }
        )
        
        created_notification = await create_notification(notification)
        created_notifications.append(created_notification)
    
    return created_notifications[0] if created_notifications else None
