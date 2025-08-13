from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DocumentVerification(BaseModel):
    url: str
    verified: bool = False
    verifiedAt: Optional[datetime] = None
    
class Certificate(BaseModel):
    name: str
    url: str
    verified: bool = False
    verifiedAt: Optional[datetime] = None

class Experience(BaseModel):
    years: int
    previousEmployers: Optional[List[str]] = []
    education: Optional[List[str]] = []
    
class BankDetails(BaseModel):
    accountNumber: str
    bankName: str
    ifscCode: str
    accountHolderName: str
    
class Earnings(BaseModel):
    total: float = 0
    pending: float = 0
    withdrawn: float = 0
    lastPayout: Optional[datetime] = None
    
class TimeSlot(BaseModel):
    start: str
    end: str
    
class DayAvailability(BaseModel):
    slots: List[TimeSlot] = []
    
class AvailabilitySchedule(BaseModel):
    monday: DayAvailability = Field(default_factory=DayAvailability)
    tuesday: DayAvailability = Field(default_factory=DayAvailability)
    wednesday: DayAvailability = Field(default_factory=DayAvailability)
    thursday: DayAvailability = Field(default_factory=DayAvailability)
    friday: DayAvailability = Field(default_factory=DayAvailability)
    saturday: DayAvailability = Field(default_factory=DayAvailability)
    sunday: DayAvailability = Field(default_factory=DayAvailability)

class StylistCreate(BaseModel):
    userId: str
    name: str
    bio: str
    location: str
    specialties: List[str]
    price: float
    experience: Experience
    availableOnline: bool = True
    availableInPerson: bool = True
    
class StylistUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    specialties: Optional[List[str]] = None
    portfolioImages: Optional[List[str]] = None
    price: Optional[float] = None
    experience: Optional[Experience] = None
    availableOnline: Optional[bool] = None
    availableInPerson: Optional[bool] = None
    availabilitySchedule: Optional[AvailabilitySchedule] = None
    bankDetails: Optional[BankDetails] = None

class StylistDB(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    name: str
    isIntern: bool = False
    location: str
    bio: str
    portfolioImages: List[str] = []
    specialties: List[str]
    price: float
    rating: float = 0
    reviewCount: int = 0
    availableOnline: bool
    availableInPerson: bool
    experience: Experience
    documents: Dict[str, Any] = {}
    applicationStatus: ApplicationStatus = ApplicationStatus.PENDING
    availabilitySchedule: AvailabilitySchedule = Field(default_factory=AvailabilitySchedule)
    bankDetails: Optional[BankDetails] = None
    earnings: Earnings = Field(default_factory=Earnings)
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class StylistResponse(BaseModel):
    id: str
    userId: str
    name: str
    isIntern: bool
    location: str
    bio: str
    portfolioImages: List[str]
    specialties: List[str]
    price: float
    rating: float
    reviewCount: int
    availableOnline: bool
    availableInPerson: bool
    experience: Experience
    applicationStatus: ApplicationStatus
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class StylistDocumentUpload(BaseModel):
    documentType: str  # "addressProof" or "certificate"
    certificateName: Optional[str] = None  # Only needed for certificates
