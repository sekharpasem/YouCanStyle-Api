from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ServiceType(str, Enum):
    ONLINE = "online"
    IN_PERSON = "in_person"
    BOTH = "both"

class ServiceCreate(BaseModel):
    stylistId: str
    title: str
    description: str
    pricePerHour: float
    serviceType: ServiceType
    duration: int  # Duration in minutes
    category: str  # e.g., 'Hair', 'Makeup', 'Nails'
    isActive: bool = True

class ServiceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    pricePerHour: Optional[float] = None
    serviceType: Optional[ServiceType] = None
    duration: Optional[int] = None
    category: Optional[str] = None
    isActive: Optional[bool] = None

class ServiceDB(BaseModel):
    id: str = Field(..., alias="_id")
    stylistId: str
    title: str
    description: str
    pricePerHour: float
    serviceType: ServiceType
    duration: int
    category: str
    isActive: bool = True
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ServiceResponse(BaseModel):
    id: str
    stylistId: str
    title: str
    description: str
    pricePerHour: float
    serviceType: ServiceType
    duration: int
    category: str
    isActive: bool
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
