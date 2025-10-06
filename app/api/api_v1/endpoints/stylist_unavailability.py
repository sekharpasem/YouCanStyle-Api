from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from app.db.mongodb import get_database
from app.db.stylist import get_stylist_by_id
from app.schemas.unavailability import (
    StylistUnavailabilityResponse,
    UnavailableSlotsResponse,
    UnavailableDate,
)

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

# ================= Add/Remove unavailable dates =================
@router.post("/{user_id}/unavailable-dates", response_model=Dict[str, Any])
@router.post("/{user_id}/unavailable-dates/", response_model=Dict[str, Any])
async def add_unavailable_date_entry(user_id: str, payload: UnavailableDate):
    """
    Add or merge an unavailable date entry on the stylist document in 'stylists'.
    If the date exists, merge slots (unique). Otherwise, push a new date entry.
    """
    # Basic validation for date format
    try:
        datetime.strptime(payload.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Expected YYYY-MM-DD",
        )

    # Ensure stylist exists
    stylist = await get_stylist_by_id(user_id)
    if not stylist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist not found")

    db = await get_database()
    stylist_oid = ObjectId(user_id)

    # Try to add slots to existing date using $addToSet
    result = await db["stylists"].update_one(
        {"_id": stylist_oid, "unavailable.date": payload.date},
        {"$addToSet": {"unavailable.$.slots": {"$each": list(set(payload.slots))}}},
    )

    if result.matched_count == 0:
        # Date entry not present; push a new one
        await db["stylists"].update_one(
            {"_id": stylist_oid},
            {"$push": {"unavailable": {"date": payload.date, "slots": list(dict.fromkeys(payload.slots))}}},
        )

    # Return updated unavailable array
    updated = await db["stylists"].find_one({"_id": stylist_oid}, {"unavailable": 1})
    return {"message": "Unavailable date saved", "unavailable": updated.get("unavailable", [])}


@router.delete("/{user_id}/unavailable-dates", response_model=Dict[str, Any])
@router.delete("/{user_id}/unavailable-dates/", response_model=Dict[str, Any])
async def delete_unavailable_date_entry(
    user_id: str,
    date: str = Query(..., description="YYYY-MM-DD"),
    slots: Optional[List[str]] = Query(None, description="Optional list of slots to remove e.g. 09:00-10:00")
):
    """
    Delete behavior:
    - If `slots` provided: remove only those slots for the given date.
      - After removal, if no slots remain OR the date is in the past, remove the entire date object.
    - If `slots` not provided: remove the date object only if it is in the past; otherwise no-op.
    """
    # Validate date format
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Expected YYYY-MM-DD",
        )

    # Ensure stylist exists
    stylist = await get_stylist_by_id(user_id)
    if not stylist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stylist not found")

    db = await get_database()
    stylist_oid = ObjectId(user_id)

    today = datetime.utcnow().date()
    is_past = date_obj.date() < today

    if slots and len(slots) > 0:
        # Remove specified slots from the date's slots array
        await db["stylists"].update_one(
            {"_id": stylist_oid, "unavailable.date": date},
            {"$pull": {"unavailable.$.slots": {"$in": slots}}},
        )

        # Check remaining slots for the date
        doc = await db["stylists"].find_one(
            {"_id": stylist_oid, "unavailable.date": date},
            {"unavailable.$": 1}
        )
        remaining_slots: List[str] = []
        if doc and "unavailable" in doc and len(doc["unavailable"]) > 0:
            remaining_slots = doc["unavailable"][0].get("slots", [])

        if is_past or len(remaining_slots) == 0:
            # Remove the entire date object if past or empty slots
            await db["stylists"].update_one(
                {"_id": stylist_oid},
                {"$pull": {"unavailable": {"date": date}}},
            )
            msg = "Unavailable date removed"
        else:
            msg = "Unavailable slots removed"
    else:
        # No specific slots provided; only remove the date if it is in the past
        if is_past:
            await db["stylists"].update_one(
                {"_id": stylist_oid},
                {"$pull": {"unavailable": {"date": date}}},
            )
            msg = "Past unavailable date removed"
        else:
            msg = "No slots provided and date is not past; nothing removed"

    # Return updated unavailable array
    updated = await db["stylists"].find_one({"_id": stylist_oid}, {"unavailable": 1})
    return {"message": msg, "unavailable": updated.get("unavailable", [])}
