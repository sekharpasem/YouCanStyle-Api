from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Optional, Dict
from app.core.auth import get_current_user
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse, BookingStatus, BookingOtpVerify, PaymentStatus, BookingReschedule, BookingLocationUpdate
from app.services.booking_service import (
    create_booking, get_booking_by_id, update_booking, cancel_booking,
    get_stylist_bookings, get_client_bookings, start_session,
    complete_booking, add_review, update_payment_status, reschedule_booking
)
from app.services.stylist_service import get_stylist_by_id, get_stylist_by_user_id
from datetime import datetime, timedelta
from app.db.stylist_availability import (
    get_unavailable_slots_by_date,
    add_unavailable_date,
    remove_unavailable_date,
)

router = APIRouter()

@router.post("/", response_model=BookingResponse)
async def create_new_booking(
    booking_in: BookingCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new booking as a client
    """
    # Check if stylist exists
    stylist = await get_stylist_by_id(booking_in.stylistId)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Create booking
    booking = await create_booking(booking_in, str(current_user["_id"]))
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create booking"
        )
    
    return booking

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get booking details (accessible to both client and stylist)
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has access to this booking
    user_id = str(current_user["_id"])
    if booking["clientId"] != user_id:
        # If not client, check if stylist
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or booking["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this booking"
            )
    
    return booking

@router.put("/{booking_id}", response_model=BookingResponse)
async def update_booking_details(
    booking_id: str,
    booking_update: BookingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update booking details (limited fields)
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has access to this booking
    user_id = str(current_user["_id"])
    if booking["clientId"] != user_id:
        # If not client, check if stylist
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or booking["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this booking"
            )
    
    # Update booking
    updated_booking = await update_booking(booking_id, booking_update)
    if not updated_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update booking"
        )
    
    return updated_booking

@router.delete("/{booking_id}", response_model=BookingResponse)
async def cancel_booking_endpoint(
    booking_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a booking
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has access to this booking
    user_id = str(current_user["_id"])
    if booking["clientId"] != user_id:
        # If not client, check if stylist
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or booking["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this booking"
            )
    
    # Cancel booking
    cancelled_booking = await cancel_booking(booking_id, reason)
    if not cancelled_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not cancel booking"
        )
    
    return cancelled_booking

@router.post("/{booking_id}/start", response_model=BookingResponse)
async def start_booking_session(
    booking_id: str,
    otp_data: BookingOtpVerify,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a booking session with OTP verification (stylist only)
    
    The stylist must provide the OTP code received from the client
    to verify and start the session.
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user is the stylist for this booking
    user_id = str(current_user["_id"])
    stylist = await get_stylist_by_user_id(user_id)
    if not stylist or booking["stylistId"] != str(stylist["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the stylist can start this session"
        )
    
    # Start session with OTP
    started_booking = await start_session(booking_id, otp_data.otpCode)
    if not started_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not start session. Check OTP code or booking status."
        )
    
    return started_booking

@router.post("/{booking_id}/complete", response_model=BookingResponse)
async def complete_booking_session(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Complete a booking session (stylist only)
    
    OTP verification is now done at session start, not completion.
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user is the stylist for this booking
    user_id = str(current_user["_id"])
    stylist = await get_stylist_by_user_id(user_id)
    if not stylist or booking["stylistId"] != str(stylist["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the stylist can complete this session"
        )
    
    # Complete session
    completed_booking = await complete_booking(booking_id)
    if not completed_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not complete session. Booking must be in progress."
        )
    
    return completed_booking

@router.post("/{booking_id}/review", response_model=BookingResponse)
async def add_booking_review(
    booking_id: str,
    rating: int = Query(..., ge=1, le=5),
    review: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a review to a completed booking (client only)
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user is the client for this booking
    user_id = str(current_user["_id"])
    if booking["clientId"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the client can review this booking"
        )
    
    # Add review
    reviewed_booking = await add_review(booking_id, rating, review)
    if not reviewed_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not add review. Booking must be completed."
        )
    
    return reviewed_booking

@router.get("/stylist/me", response_model=List[BookingResponse])
async def get_my_stylist_bookings(
    status: Optional[BookingStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get bookings for the current user as a stylist
    """
    # Get stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Get bookings
    bookings = await get_stylist_bookings(
        str(stylist["_id"]),
        status=status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    
    return bookings

@router.get("/client/me", response_model=List[BookingResponse])
async def get_my_client_bookings(
    status: Optional[BookingStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get bookings for the current user as a client
    """
    # Get bookings
    bookings = await get_client_bookings(
        str(current_user["_id"]),
        status=status,
        skip=skip,
        limit=limit
    )
    
    return bookings



@router.put("/{booking_id}/payment-status", response_model=BookingResponse)
async def update_booking_payment_status(
    booking_id: str,
    payment_status: PaymentStatus = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the payment status of a booking (requires admin or stylist permissions)
    
    - **payment_status**: New payment status (PENDING, COMPLETED, FAILED)
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has appropriate permissions
    user_id = str(current_user["_id"])
    is_admin = current_user.get("isAdmin", False)
    
    # If not admin, check if stylist for this booking
    if not is_admin:
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or booking["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the stylist or admin can update payment status"
            )
    
    # Update payment status
    updated_booking = await update_payment_status(booking_id, payment_status)
    if not updated_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update payment status"
        )
    
    return updated_booking

@router.post("/{booking_id}/reschedule", response_model=BookingResponse)
async def reschedule_booking_endpoint(
    booking_id: str,
    reschedule_data: BookingReschedule,
    current_user: dict = Depends(get_current_user)
):
    """
    Reschedule a booking to a new date and time
    
    - **date**: New date for the booking
    - **startTime**: New start time (format: HH:MM)
    - **endTime**: New end time (format: HH:MM)
    - **reason**: Optional reason for rescheduling
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has access to this booking
    user_id = str(current_user["_id"])
    is_admin = current_user.get("isAdmin", False)
    
    # Check if client or stylist for this booking
    is_client = booking["clientId"] == user_id
    
    stylist = None
    is_stylist = False
    if not is_client:
        stylist = await get_stylist_by_user_id(user_id)
        is_stylist = stylist and booking["stylistId"] == str(stylist["_id"])
    
    if not (is_client or is_stylist or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to reschedule this booking"
        )
    
    # Helpers
    def _to_date_str(d: Optional[datetime | str]) -> str:
        if isinstance(d, datetime):
            return d.strftime("%Y-%m-%d")
        if isinstance(d, str):
            # Try ISO with/without Z; fallback to date-only
            try:
                s = d.replace("Z", "")
                return datetime.fromisoformat(s).strftime("%Y-%m-%d")
            except Exception:
                try:
                    return datetime.strptime(d, "%Y-%m-%d").strftime("%Y-%m-%d")
                except Exception:
                    # As a last resort, take first 10 chars
                    return d[:10]
        # Unknown type
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format in booking")

    def _parse_hhmm(hhmm: str) -> datetime:
        try:
            return datetime.strptime(hhmm, "%H:%M")
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid time format: {hhmm}")

    def _hour_segments(start_hhmm: str, end_hhmm: str) -> List[str]:
        """Split inclusive start to exclusive end into 60-min segments: ["10:00-11:00", ...]"""
        start_dt = _parse_hhmm(start_hhmm)
        end_dt = _parse_hhmm(end_hhmm)
        if end_dt <= start_dt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="endTime must be after startTime")
        segs: List[str] = []
        cur = start_dt
        while cur < end_dt:
            nxt = cur + timedelta(hours=1)
            # Clamp to end to avoid overshoot if non-exact hour duration
            if nxt > end_dt:
                nxt = end_dt
            segs.append(f"{cur.strftime('%H:%M')}-{nxt.strftime('%H:%M')}")
            cur = nxt
        return segs

    stylist_id = booking["stylistId"]

    # Old schedule details
    old_date_str = _to_date_str(booking.get("date"))
    old_start = booking.get("startTime")
    old_end = booking.get("endTime")
    if not old_start or not old_end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing booking times missing")
    old_segments = _hour_segments(old_start, old_end)

    # New schedule details
    new_date_str = _to_date_str(reschedule_data.date)
    new_start = reschedule_data.startTime
    new_end = reschedule_data.endTime
    new_segments = _hour_segments(new_start, new_end)

    # 1) Remove old unavailability slots
    try:
        existing_old_slots = await get_unavailable_slots_by_date(stylist_id, old_date_str)
        # Remove just the old segments; keep others
        updated_old_slots = [s for s in existing_old_slots if s not in set(old_segments)]
        if len(updated_old_slots) == 0:
            # No more slots on that day, remove the date entirely
            await remove_unavailable_date(stylist_id, old_date_str)
        else:
            await add_unavailable_date(stylist_id, old_date_str, updated_old_slots)
    except Exception as e:
        # If we cannot free old slots, better to fail early to avoid inconsistent state
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to remove old unavailability: {e}")

    # 2) Perform the reschedule
    try:
        rescheduled_booking = await reschedule_booking(
            booking_id,
            reschedule_data.date,
            reschedule_data.startTime,
            reschedule_data.endTime,
            reschedule_data.reason
        )
        if not rescheduled_booking:
            # Rollback: try to restore old slots
            try:
                existing_old_slots = await get_unavailable_slots_by_date(stylist_id, old_date_str)
                restored = list(set(existing_old_slots) | set(old_segments))
                await add_unavailable_date(stylist_id, old_date_str, restored)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not reschedule booking. It may be completed, cancelled, or in an invalid state."
            )
    except HTTPException:
        raise
    except Exception as e:
        # Rollback: try to restore old slots
        try:
            existing_old_slots = await get_unavailable_slots_by_date(stylist_id, old_date_str)
            restored = list(set(existing_old_slots) | set(old_segments))
            await add_unavailable_date(stylist_id, old_date_str, restored)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reschedule failed: {e}")

    # 3) Add new unavailability slots (best-effort). If it fails, booking remains rescheduled.
    try:
        existing_new_slots = await get_unavailable_slots_by_date(stylist_id, new_date_str)
        merged_new = list(dict.fromkeys(existing_new_slots + new_segments))  # preserve order, dedupe
        await add_unavailable_date(stylist_id, new_date_str, merged_new)
    except Exception:
        # Log in real system; for now, proceed to return rescheduled booking
        pass

    return rescheduled_booking

@router.put("/{booking_id}/location", response_model=BookingResponse)
async def update_booking_location(
    booking_id: str,
    location_data: BookingLocationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the meeting location and coordinates for a booking
    
    - **location**: Meeting location name/address
    - **coordinates**: Latitude and longitude coordinates
    """
    # Get booking
    booking = await get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if user has access to this booking
    user_id = str(current_user["_id"])
    is_admin = current_user.get("isAdmin", False)
    
    # Check if client or stylist for this booking
    is_client = booking["clientId"] == user_id
    
    stylist = None
    is_stylist = False
    if not is_client:
        stylist = await get_stylist_by_user_id(user_id)
        is_stylist = stylist and booking["stylistId"] == str(stylist["_id"])
    
    if not (is_client or is_stylist or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to update this booking's location"
        )
    
    # Check if booking can be updated (not completed or cancelled)
    if booking["status"] in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update location for completed or cancelled bookings"
        )
    
    # Update location and coordinates
    from app.services.booking_service import update_booking_location
    updated_booking = await update_booking_location(
        booking_id,
        location_data.location,
        location_data.coordinates.model_dump()
    )
    
    if not updated_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update booking location"
        )
    
    return updated_booking
