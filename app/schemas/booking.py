from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "noShow"
    RESCHEDULED = "rescheduled"
    
class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    FAILED = "failed"

class Coordinates(BaseModel):
    lat: float
    lng: float

class BookingCreate(BaseModel):
    stylistId: str
    date: datetime
    startTime: str
    endTime: str
    services: List[str]
    price: int
    duration: int
    isOnlineSession: bool
    location: Optional[str] = None
    notes: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    
class BookingUpdate(BaseModel):
    date: Optional[datetime] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    status: Optional[BookingStatus] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    
class BookingDB(BaseModel):
    id: str = Field(..., alias="_id")
    stylistId: str
    clientId: str
    clientName: str
    clientImage: Optional[str] = None
    date: datetime
    startTime: str
    endTime: str
    services: List[str]
    price: int
    duration: int
    isOnlineSession: bool
    location: Optional[str] = None
    status: BookingStatus = BookingStatus.PENDING
    notes: Optional[str] = None
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    meetingLink: Optional[str] = None
    paymentStatus: PaymentStatus = PaymentStatus.PENDING
    paymentId: Optional[str] = None
    otpCode: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    rating: Optional[int] = None
    review: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class BookingResponse(BaseModel):
    id: str
    stylistId: str
    clientId: str
    clientName: str
    clientImage: Optional[str] = None
    date: datetime
    startTime: str
    endTime: str
    services: List[str]
    price: int
    duration: int
    isOnlineSession: bool
    location: Optional[str] = None
    status: BookingStatus
    notes: Optional[str] = None
    createdAt: datetime
    meetingLink: Optional[str] = None
    paymentStatus: PaymentStatus
    coordinates: Optional[Coordinates] = None
    rating: Optional[int] = None
    review: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class BookingOtpVerify(BaseModel):
    otpCode: str
