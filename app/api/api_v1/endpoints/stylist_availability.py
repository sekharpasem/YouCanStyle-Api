from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import logging

from app.db.mongodb import db
from app.core.auth import get_current_user
from app.schemas.stylist import UnavailableSlot

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/stylists/{stylist_id}/unavailable-dates", response_model=List[str])
async def get_stylist_unavailable_dates(
    stylist_id: str = Path(..., title="The ID of the stylist"),
    month: Optional[int] = Query(None, description="Month (1-12)"),
    year: Optional[int] = Query(None, description="Year (e.g., 2025)")
):
    """
    Get a list of dates when a stylist is unavailable.
    Optionally filter by month and year.
    """
    try:
        # Find the stylist
        try:
            stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)})
        except:
            stylist = await db.db.stylists.find_one({"id": stylist_id})
            
        if not stylist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stylist not found"
            )
            
        # Get unavailable dates
        unavailable_dates = []
        unavailable_slots = stylist.get("unavailable", [])
        
        for slot in unavailable_slots:
            date_str = slot.get("date", "")
            
            # Skip if date is invalid
            if not date_str:
                continue
                
            try:
                # Parse the date
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                
                # Apply month/year filters if specified
                if month is not None and date_obj.month != month:
                    continue
                if year is not None and date_obj.year != year:
                    continue
                    
                # Add to results if not already included
                if date_str not in unavailable_dates:
                    unavailable_dates.append(date_str)
            except ValueError:
                logger.warning(f"Invalid date format in stylist unavailable slots: {date_str}")
                continue
            
        return unavailable_dates
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_stylist_unavailable_dates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving unavailable dates"
        )

@router.get("/stylists/{stylist_id}/unavailable-slots/{date}", response_model=List[str])
async def get_stylist_unavailable_slots(
    stylist_id: str = Path(..., title="The ID of the stylist"),
    date: str = Path(..., title="Date in YYYY-MM-DD format")
):
    """
    Get a list of time slots when a stylist is unavailable on a specific date.
    """
    try:
        # Validate date format
        try:
            date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
            
        # Find the stylist
        try:
            stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)})
        except:
            stylist = await db.db.stylists.find_one({"id": stylist_id})
            
        if not stylist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stylist not found"
            )
            
        # Get unavailable slots for the specified date
        unavailable_slots = []
        
        for slot in stylist.get("unavailable", []):
            if slot.get("date") == date:
                unavailable_slots.extend(slot.get("slots", []))
                
        return unavailable_slots
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_stylist_unavailable_slots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while retrieving unavailable slots"
        )
