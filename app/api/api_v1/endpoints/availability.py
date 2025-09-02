from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from app.core.auth import get_current_user
from app.schemas.stylist import AvailabilitySchedule, TimeSlot, DayAvailability
from app.services.stylist_service import (
    get_stylist_by_id, get_stylist_by_user_id,
    get_availability, update_availability, update_day_availability,
    get_available_dates
)
from datetime import date
from pydantic import BaseModel

router = APIRouter()

class DaySlots(BaseModel):
    day: str
    slots: List[TimeSlot]

@router.get("/{stylist_id}", response_model=Dict[str, Any])
async def get_stylist_availability(stylist_id: str):
    """
    Get a stylist's full availability schedule
    """
    # Check if stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Get availability
    availability = await get_availability(stylist_id)
    return availability or {}

@router.get("/{stylist_id}/dates", response_model=List[int])
async def get_stylist_available_dates(
    stylist_id: str, 
    year: int = Query(..., description="Year to check availability for"),
    month: int = Query(..., description="Month to check availability for (1-12)")
):
    """
    Get a stylist's available dates for a specific month and year
    """
    # Validate month input
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12"
        )
    
    # Check if stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Get available dates
    available_dates = await get_available_dates(stylist_id, year, month)
    return available_dates

@router.get("/me", response_model=Dict[str, Any])
async def get_my_availability(current_user: dict = Depends(get_current_user)):
    """
    Get current stylist's availability schedule
    """
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Get availability
    availability = await get_availability(str(stylist["_id"]))
    return availability or {}

@router.put("/me", response_model=Dict[str, Any])
async def update_my_availability(
    availability_data: AvailabilitySchedule,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current stylist's full availability schedule
    """
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Update availability
    success = await update_availability(str(stylist["_id"]), availability_data.dict())
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update availability"
        )
    
    # Get updated availability
    updated_availability = await get_availability(str(stylist["_id"]))
    return {"message": "Availability updated successfully", "availability": updated_availability}

@router.put("/me/{day}", response_model=Dict[str, Any])
async def update_my_day_availability(
    day: str,
    day_slots: DaySlots,
    current_user: dict = Depends(get_current_user)
):
    """
    Update availability for a specific day
    """
    # Validate day matches the path parameter
    if day.lower() != day_slots.day.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Day in path must match day in request body"
        )
    
    # Check if day is valid
    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day.lower() not in valid_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid day. Must be one of: monday, tuesday, wednesday, thursday, friday, saturday, sunday"
        )
    
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Convert slots to dict format
    slots_data = [slot.dict() for slot in day_slots.slots]
    
    # Update day availability
    success = await update_day_availability(str(stylist["_id"]), day.lower(), slots_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update day availability"
        )
    
    # Get updated availability
    updated_availability = await get_availability(str(stylist["_id"]))
    return {"message": f"Availability for {day} updated successfully", "availability": updated_availability}
