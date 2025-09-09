from pydantic import BaseModel
from typing import List, Optional

class UnavailableDate(BaseModel):
    date: str  # Format: "2025-09-05"
    slots: List[str] = []  # Format: ["14:00-16:00", "18:00-20:00"]

class StylistUnavailability(BaseModel):
    unavailable: List[UnavailableDate] = []

class StylistUnavailabilityResponse(BaseModel):
    userId: str
    year: int
    month: int
    unavailableDates: List[str]

class UnavailableSlotsResponse(BaseModel):
    userId: str
    date: str
    unavailableSlots: List[str]
