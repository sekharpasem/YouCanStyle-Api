from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.stylist import get_stylist_by_id
from app.schemas.unavailability import StylistUnavailabilityResponse, UnavailableSlotsResponse

router = APIRouter()

@router.get("/{user_id}/unavailable-dates", response_model=StylistUnavailabilityResponse)
async def get_user_unavailable_dates(
    user_id: str, 
    year: int = Query(..., description="Year to check unavailability for"),
    month: int = Query(..., description="Month to check unavailability for (1-12)")
):
    """
    Get a stylist's unavailable dates for a specific month and year.
    Returns only dates where all default slots are blocked.
    """
    # Validate month input
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Month must be between 1 and 12"
        )
    
    # Check if stylist exists
    stylist = await get_stylist_by_id(user_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Filter dates for the specified year and month
    month_str = f"{month:02d}"
    year_str = str(year)
    date_prefix = f"{year_str}-{month_str}"
    
    unavailable_dates = []
    
    # Check the unavailable field in the stylist document
    for unavailable_slot in stylist.get("unavailable", []):
        date = unavailable_slot.get("date", "")
        if date.startswith(date_prefix):
            # Assuming a date with all slots unavailable means the entire day is unavailable
            # This logic can be adjusted based on business requirements
            unavailable_dates.append(date)
    
    return {
        "userId": user_id,
        "year": year,
        "month": month,
        "unavailableDates": unavailable_dates
    }

@router.get("/{user_id}/unavailable-slots", response_model=UnavailableSlotsResponse)
async def get_user_unavailable_slots(
    user_id: str,
    year: int = Query(..., description="Year to check unavailability for"),
    month: int = Query(..., description="Month to check unavailability for (1-12)"),
    date: int = Query(..., description="Day of the month to check unavailability for (1-31)")
):
    """
    Get a stylist's unavailable slots for a specific date
    """
    # Validate date inputs
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Month must be between 1 and 12"
        )
        
    if date < 1 or date > 31:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Date must be between 1 and 31"
        )
    
    # Check if stylist exists
    stylist = await get_stylist_by_id(user_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Format the date string
    formatted_date = f"{year}-{month:02d}-{date:02d}"
    
    # Find the unavailable slots for this date
    unavailable_slots = []
    for unavailable_slot in stylist.get("unavailable", []):
        if unavailable_slot.get("date") == formatted_date:
            unavailable_slots = unavailable_slot.get("slots", [])
            break
    
    return {
        "userId": user_id,
        "date": formatted_date,
        "unavailableSlots": unavailable_slots
    }
