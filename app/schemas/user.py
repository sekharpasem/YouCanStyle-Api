from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    phone: str
    fullName: str
    
class UserCreate(UserBase):
    password: str
    role: str = "client"
    
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    fullName: Optional[str] = None
    profileImage: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    fcmToken: Optional[str] = None
    
class UserDB(UserBase):
    id: str = Field(..., alias="_id")
    role: str
    profileImage: Optional[str] = None
    createdAt: datetime
    lastLogin: Optional[datetime] = None
    isActive: bool = True
    settings: Dict[str, Any]
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    phone: str
    fullName: str
    role: str
    profileImage: Optional[str] = None
    createdAt: datetime
    lastLogin: Optional[datetime] = None
    isActive: bool
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
