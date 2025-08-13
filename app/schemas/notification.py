from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    BOOKING_CREATED = "booking_created"
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_COMPLETED = "booking_completed"
    BOOKING_REMINDER = "booking_reminder"
    CHAT_MESSAGE = "chat_message"
    PAYMENT_RECEIVED = "payment_received"
    STYLIST_AVAILABILITY = "stylist_availability"
    SYSTEM = "system"

class NotificationCreate(BaseModel):
    userId: str
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    
class NotificationUpdate(BaseModel):
    read: Optional[bool] = None
    readAt: Optional[datetime] = None

class NotificationResponse(BaseModel):
    id: str
    userId: str
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    readAt: Optional[datetime] = None
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class NotificationSettings(BaseModel):
    bookingUpdates: bool = True
    chatMessages: bool = True
    promotions: bool = True
    reminders: bool = True
    email: bool = True
    push: bool = True
    
    class Config:
        populate_by_name = True

class PushRegistrationCreate(BaseModel):
    userId: str
    deviceToken: str
    deviceType: str  # "ios" or "android"
    
class PushRegistrationResponse(BaseModel):
    id: str
    userId: str
    deviceToken: str
    deviceType: str
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
