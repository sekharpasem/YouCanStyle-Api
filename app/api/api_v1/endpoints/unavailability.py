from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.schemas.unavailability import StylistUnavailability, UnavailableDate
from app.core.auth import get_current_user
from app.db.stylist import get_stylist_by_id, get_stylist_by_user_id
from app.db.stylist_availability import (
    get_unavailable_dates_by_month, 
    get_unavailable_slots_by_date,
    update_unavailability,
    add_unavailable_date,
    remove_unavailable_date
)

router = APIRouter()

@router.get("/{stylist_id}/unavailable-dates", response_model=List[Dict[str, Any]])
async def get_stylist_unavailable_dates(
    stylist_id: str, 
    year: int = Query(..., description="Year to check availability for"),
    month: int = Query(..., description="Month to check availability for (1-12)")
):
    """
    Get a stylist's unavailable dates for a specific month and year
    """
    # Validate month input
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Month must be between 1 and 12"
        )
    
    # Check if stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Get unavailable dates
    unavailable_dates = await get_unavailable_dates_by_month(stylist_id, year, month)
    return unavailable_dates

@router.get("/{stylist_id}/unavailable-slots", response_model=Dict[str, List[str]])
async def get_stylist_unavailable_slots(
    stylist_id: str, 
    date: str = Query(..., description="Date to check time slots for (YYYY-MM-DD format)")
):
    """
    Get a stylist's unavailable time slots for a specific date
    """
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Check if stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Get unavailable slots for the date
    unavailable_slots = await get_unavailable_slots_by_date(stylist_id, date)
    return {"unavailable_slots": unavailable_slots}

@router.put("/me/unavailability", response_model=Dict[str, Any])
async def update_my_unavailability(
    unavailability_data: StylistUnavailability,
    current_user: dict = Depends(get_current_user)
):
    """
    Update current stylist's unavailable dates and slots
    """
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Update unavailability
    success = await update_unavailability(str(stylist["_id"]), unavailability_data.dict())
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update unavailability"
        )
    
    return {"message": "Unavailability updated successfully"}

@router.put("/me/unavailable-date", response_model=Dict[str, Any])
async def add_my_unavailable_date(
    unavailable_date: UnavailableDate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add or update an unavailable date with its slots for current stylist
    """
    # Validate date format
    try:
        datetime.strptime(unavailable_date.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Add/update unavailable date
    success = await add_unavailable_date(
        str(stylist["_id"]), 
        unavailable_date.date, 
        unavailable_date.slots
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update unavailable date"
        )
    
    return {"message": f"Unavailability for date {unavailable_date.date} updated successfully"}

@router.delete("/me/unavailable-date/{date}", response_model=Dict[str, Any])
async def remove_my_unavailable_date(
    date: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove an unavailable date for current stylist
    """
    # Validate date format
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Get current stylist
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Remove unavailable date
    success = await remove_unavailable_date(str(stylist["_id"]), date)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove unavailable date"
        )
    
    return {"message": f"Unavailability for date {date} removed successfully"}
