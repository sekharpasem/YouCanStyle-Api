from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class FavoriteBase(BaseModel):
    """Base schema for favorite operations"""
    stylistId: str


class FavoriteCreate(FavoriteBase):
    """Schema for creating a favorite"""
    action: str = Field(..., description="Action to perform: 'add' or 'remove'")


class FavoriteResponse(FavoriteBase):
    """Schema for favorite response"""
    id: str = Field(..., alias="_id")
    userId: str
    createdAt: datetime
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class FavoritesListResponse(BaseModel):
    """Schema for list of favorites response"""
    favorites: List[FavoriteResponse]
    total: int
    skip: int
    limit: int
