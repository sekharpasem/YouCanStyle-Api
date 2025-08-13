from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class AttachmentType(str, Enum):
    IMAGE = "image"
    FILE = "file"
    LOCATION = "location"
    CONTACT = "contact"

class Attachment(BaseModel):
    type: AttachmentType
    url: str
    name: Optional[str] = None
    size: Optional[int] = None

class ChatRoomCreate(BaseModel):
    participantId: str  # The ID of the other participant (user will add self)
    bookingId: Optional[str] = None
    
class MessageCreate(BaseModel):
    chatRoomId: str
    message: str
    attachments: Optional[List[Attachment]] = None
    systemMessage: bool = False

class MessageDB(BaseModel):
    id: str = Field(..., alias="_id")
    chatRoomId: str
    senderId: str
    message: str
    timestamp: datetime
    read: bool = False
    attachments: Optional[List[Attachment]] = None
    systemMessage: bool = False
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class MessageResponse(BaseModel):
    id: str
    chatRoomId: str
    senderId: str
    message: str
    timestamp: datetime
    read: bool
    attachments: Optional[List[Attachment]] = None
    systemMessage: bool
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ChatRoomDB(BaseModel):
    id: str = Field(..., alias="_id")
    participants: List[str]
    lastMessage: Optional[str] = None
    lastMessageTime: Optional[datetime] = None
    createdAt: datetime
    unreadCounts: dict = Field(default_factory=dict)
    bookingId: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ChatRoomResponse(BaseModel):
    id: str
    participants: List[str]
    lastMessage: Optional[str] = None
    lastMessageTime: Optional[datetime] = None
    createdAt: datetime
    unreadCount: int = 0  # For the current user
    bookingId: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ChatRoomWithParticipantsResponse(ChatRoomResponse):
    participantDetails: List[Any] = []  # Will contain user details
