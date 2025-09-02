from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Optional, Dict
from app.core.auth import get_current_user
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse, BookingStatus, BookingOtpVerify, PaymentStatus, BookingReschedule
from app.services.booking_service import (
    create_booking, get_booking_by_id, update_booking, cancel_booking,
    get_stylist_bookings, get_client_bookings, start_session,
    complete_booking, add_review, update_payment_status, reschedule_booking
)
from app.services.stylist_service import get_stylist_by_id, get_stylist_by_user_id
from datetime import datetime, timedelta

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
    current_user: dict = Depends(get_current_user)
):
    """
    Start a booking session (stylist only)
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
    
    # Start session
    started_booking = await start_session(booking_id)
    if not started_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not start session"
        )
    
    return started_booking

@router.post("/{booking_id}/complete", response_model=BookingResponse)
async def complete_booking_session(
    booking_id: str,
    otp_data: BookingOtpVerify,
    current_user: dict = Depends(get_current_user)
):
    """
    Complete a booking session with OTP verification (stylist only)
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
    
    # Complete session with OTP
    completed_booking = await complete_booking(booking_id, otp_data.otpCode)
    if not completed_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not complete session. Check OTP code."
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
    
    # Perform the reschedule
    rescheduled_booking = await reschedule_booking(
        booking_id,
        reschedule_data.date,
        reschedule_data.startTime,
        reschedule_data.endTime,
        reschedule_data.reason
    )
    
    if not rescheduled_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not reschedule booking. It may be completed, cancelled, or in an invalid state."
        )
    
    return rescheduled_booking
