from typing import List, Dict, Any, Optional
from datetime import datetime
from app.db.mongodb import db

async def get_unavailable_dates_by_month(stylist_id: str, year: int, month: int) -> List[Dict[str, Any]]:
    """Get stylist's unavailable dates for a specific month and year"""
    # Create date pattern for filtering (YYYY-MM)
    date_pattern = f"{year:04d}-{month:02d}"
    
    result = await db.stylist_unavailability.find_one({"stylist_id": stylist_id})
    
    if not result or not result.get("unavailable"):
        return []
        
    # Filter dates by month
    filtered_dates = [
        {
            "date": date_item["date"],
            "slots": date_item["slots"]
        }
        for date_item in result.get("unavailable", [])
        if date_item["date"].startswith(date_pattern)
    ]
    
    return filtered_dates

async def get_unavailable_slots_by_date(stylist_id: str, date: str) -> List[str]:
    """Get stylist's unavailable time slots for a specific date"""
    result = await db.stylist_unavailability.find_one(
        {"stylist_id": stylist_id}
    )
    
    if not result or not result.get("unavailable"):
        return []
    
    # Extract slots for the specific date
    for date_item in result.get("unavailable", []):
        if date_item["date"] == date:
            return date_item.get("slots", [])
    
    return []

async def update_unavailability(stylist_id: str, unavailability_data: Dict[str, Any]) -> bool:
    """Update stylist's unavailable dates and slots"""
    result = await db.stylist_unavailability.update_one(
        {"stylist_id": stylist_id},
        {"$set": unavailability_data},
        upsert=True
    )
    return result.acknowledged

async def add_unavailable_date(stylist_id: str, date: str, slots: List[str]) -> bool:
    """Add or update an unavailable date with its slots"""
    # First check if this date already exists in the unavailable list
    result = await db.stylist_unavailability.find_one(
        {"stylist_id": stylist_id, "unavailable.date": date}
    )
    
    if result:
        # Update existing date's slots
        update_result = await db.stylist_unavailability.update_one(
            {"stylist_id": stylist_id, "unavailable.date": date},
            {"$set": {"unavailable.$.slots": slots}}
        )
        return update_result.acknowledged
    else:
        # Add new date to the unavailable list
        update_result = await db.stylist_unavailability.update_one(
            {"stylist_id": stylist_id},
            {"$push": {"unavailable": {"date": date, "slots": slots}}},
            upsert=True
        )
        return update_result.acknowledged

async def remove_unavailable_date(stylist_id: str, date: str) -> bool:
    """Remove an unavailable date from the stylist's unavailability"""
    result = await db.stylist_unavailability.update_one(
        {"stylist_id": stylist_id},
        {"$pull": {"unavailable": {"date": date}}}
    )
    return result.acknowledged
