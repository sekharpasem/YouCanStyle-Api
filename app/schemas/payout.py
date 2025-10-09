from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PayoutStatus(str, Enum):
    pending = "pending"
    success = "success"


class PayoutCreate(BaseModel):
    stylistName: str = Field(..., description="Stylist display name")
    stylistId: str = Field(..., description="ID of the stylist (ObjectId as string)")
    bookingId: str = Field(..., description="Related booking ID")
    amount: float = Field(..., ge=0, description="Gross payout amount for the booking")
    status: PayoutStatus = Field(..., description="Payout status: pending | success")


class PayoutResponse(BaseModel):
    id: str
    stylistName: str
    stylistId: str
    bookingId: str
    amount: float
    commission: float
    status: PayoutStatus
    createdAt: datetime


class PayoutSummaryResponse(BaseModel):
    weeklyEarnings: float = 0.0
    monthlyEarnings: float = 0.0
    pendingPayouts: float = 0.0
