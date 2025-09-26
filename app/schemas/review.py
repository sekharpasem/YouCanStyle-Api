from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ReviewBase(BaseModel):
    review: str
    rating: int = Field(..., ge=1, le=5)


class ReviewCreate(ReviewBase):
    userId: str
    stylistId: str
    createdAt: Optional[datetime] = None


class ReviewResponse(ReviewBase):
    id: str = Field(..., alias="_id")
    userId: str
    stylistId: str
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
