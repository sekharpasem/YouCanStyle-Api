from typing import Dict, Any, List, Optional
from app.db.mongodb import db
from app.schemas.booking import BookingCreate, BookingUpdate, BookingStatus, PaymentStatus
from app.services.user_service import get_user_by_id
from datetime import datetime, timedelta
import random
import string
from bson import ObjectId

async def create_booking(booking_in: BookingCreate, client_id: str) -> Dict[str, Any]:
    """
    Create a new booking
    """
    # Get client info
    client = await get_user_by_id(client_id)
    if not client:
        return None
    
    # Create booking data
    booking_data = booking_in.dict()
    booking_data["clientId"] = client_id
    booking_data["clientName"] = client.get("fullName", "")
    booking_data["clientImage"] = client.get("profileImage", "")
    booking_data["status"] = BookingStatus.PENDING
    booking_data["createdAt"] = datetime.utcnow()
    booking_data["paymentStatus"] = PaymentStatus.PENDING
    
    # Generate OTP code for session verification
    booking_data["otpCode"] = ''.join(random.choices(string.digits, k=4))
    
    # Generate meeting link for online sessions
    if booking_in.isOnlineSession:
        booking_data["meetingLink"] = f"https://meet.youcanstyle.com/{random.randint(10000000, 99999999)}"
    
    # Insert booking into database
    result = await db.db.bookings.insert_one(booking_data)
    
    # Get the created booking
    created_booking = await db.db.bookings.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_booking["id"] = str(created_booking["_id"])
    
    return created_booking

async def get_booking_by_id(booking_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a booking by ID
    """
    try:
        booking = await db.db.bookings.find_one({"_id": ObjectId(booking_id)})
        if booking:
            booking["id"] = str(booking["_id"])
        return booking
    except:
        return None

async def update_booking(booking_id: str, booking_update: BookingUpdate) -> Optional[Dict[str, Any]]:
    """
    Update a booking
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Update only provided fields
    update_data = booking_update.dict(exclude_unset=True)
    
    if update_data:
        # Add updated timestamp
        update_data["updatedAt"] = datetime.utcnow()
        
        # Update booking in database
        await db.db.bookings.update_one(
            {"_id": ObjectId(booking_id)},
            {"$set": update_data}
        )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking

async def cancel_booking(booking_id: str, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Cancel a booking
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Check if booking can be cancelled
    if booking["status"] in [BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW]:
        return None
    
    # Update booking status
    update_data = {
        "status": BookingStatus.CANCELLED,
        "updatedAt": datetime.utcnow()
    }
    
    if reason:
        update_data["cancellationReason"] = reason
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking

async def complete_booking(booking_id: str) -> Optional[Dict[str, Any]]:
    """
    Complete a booking (no OTP verification needed, since it was verified at start)
    
    Args:
        booking_id: The ID of the booking to complete
        
    Returns:
        Updated booking or None if booking not found or not in progress
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Check if booking is in progress
    if booking["status"] != BookingStatus.IN_PROGRESS:
        return None
    
    # Update booking status
    update_data = {
        "status": BookingStatus.COMPLETED,
        "updatedAt": datetime.utcnow()
    }
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking

async def get_stylist_bookings(
    stylist_id: str,
    status: Optional[BookingStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get bookings for a stylist
    """
    # Build query
    query = {"stylistId": stylist_id}
    
    if status:
        query["status"] = status
        
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    elif start_date:
        query["date"] = {"$gte": start_date}
    elif end_date:
        query["date"] = {"$lte": end_date}
    
    # Execute query
    cursor = db.db.bookings.find(query).skip(skip).limit(limit).sort("date", 1)
    bookings = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for booking in bookings:
        booking["id"] = str(booking["_id"])
    
    return bookings

async def get_client_bookings(
    client_id: str,
    status: Optional[BookingStatus] = None,
    skip: int = 0,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get bookings for a client
    """
    # Build query
    query = {"clientId": client_id}
    
    if status:
        query["status"] = status
    
    # Execute query
    cursor = db.db.bookings.find(query).skip(skip).limit(limit).sort("date", -1)
    bookings = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for booking in bookings:
        booking["id"] = str(booking["_id"])
    
    return bookings

async def start_session(booking_id: str, otp_code: str) -> Optional[Dict[str, Any]]:
    """
    Start a booking session with OTP verification
    
    Args:
        booking_id: The ID of the booking to start
        otp_code: OTP code provided by the client for verification
        
    Returns:
        Updated booking or None if booking not found or OTP invalid
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Check if booking is confirmed
    if booking["status"] != BookingStatus.CONFIRMED:
        return None
    
    # Verify OTP code
    if booking.get("otpCode") != otp_code:
        return None
    
    # Update booking status
    update_data = {
        "status": BookingStatus.IN_PROGRESS,
        "updatedAt": datetime.utcnow()
    }
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking

async def add_review(booking_id: str, rating: int, review: str) -> Optional[Dict[str, Any]]:
    """
    Add review to a booking
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Check if booking is completed
    if booking["status"] != BookingStatus.COMPLETED:
        return None
    
    # Update booking with review
    update_data = {
        "rating": rating,
        "review": review,
        "updatedAt": datetime.utcnow()
    }
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    
    # Update stylist rating
    await update_stylist_rating(booking["stylistId"])
    
    return updated_booking

async def update_stylist_rating(stylist_id: str) -> None:
    """
    Update stylist rating based on all reviews
    """
    # Get all completed bookings with ratings for this stylist
    pipeline = [
        {"$match": {"stylistId": stylist_id, "rating": {"$exists": True, "$ne": None}}},
        {"$group": {
            "_id": "$stylistId",
            "averageRating": {"$avg": "$rating"},
            "count": {"$sum": 1}
        }}
    ]
    
    result = await db.db.bookings.aggregate(pipeline).to_list(length=1)
    
    if result:
        avg_rating = result[0]["averageRating"]
        review_count = result[0]["count"]
        
        # Update stylist rating
        await db.db.stylists.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$set": {
                "rating": round(avg_rating, 1),
                "reviewCount": review_count
            }}
        )

async def update_payment_status(booking_id: str, payment_status: PaymentStatus) -> Optional[Dict[str, Any]]:
    """
    Update the payment status of a booking
    
    Args:
        booking_id: The ID of the booking to update
        payment_status: New payment status (PENDING, COMPLETED, FAILED)
        
    Returns:
        Updated booking or None if booking not found
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Update payment status
    update_data = {
        "paymentStatus": payment_status,
        "updatedAt": datetime.utcnow()
    }
    
    # If payment is completed, also update booking status to CONFIRMED if it was PENDING
    if payment_status == PaymentStatus.COMPLETED and booking["status"] == BookingStatus.PENDING:
        update_data["status"] = BookingStatus.CONFIRMED
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking

async def reschedule_booking(
    booking_id: str, 
    date: datetime, 
    start_time: str, 
    end_time: str, 
    reason: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Reschedule a booking by updating date and time
    
    Args:
        booking_id: The ID of the booking to reschedule
        date: New date for the booking
        start_time: New start time (format: HH:MM)
        end_time: New end time (format: HH:MM)
        reason: Optional reason for rescheduling
        
    Returns:
        Updated booking or None if booking not found or cannot be rescheduled
    """
    # Get the current booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        return None
    
    # Check if booking can be rescheduled
    # Can't reschedule completed, cancelled or no-show bookings
    if booking["status"] in [BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.NO_SHOW]:
        return None
    
    # Update booking data
    update_data = {
        "date": date,
        "startTime": start_time,
        "endTime": end_time,
        "status": BookingStatus.RESCHEDULED,
        "updatedAt": datetime.utcnow()
    }
    
    # Add reason if provided
    if reason:
        update_data["rescheduleReason"] = reason
    
    # Update booking in database
    await db.db.bookings.update_one(
        {"_id": ObjectId(booking_id)},
        {"$set": update_data}
    )
    
    # Get the updated booking
    updated_booking = await get_booking_by_id(booking_id)
    return updated_booking
