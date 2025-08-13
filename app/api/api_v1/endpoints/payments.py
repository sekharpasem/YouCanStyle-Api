from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Dict, Any, Optional
from app.core.auth import get_current_user
from app.schemas.payment import (
    PaymentCreate, PaymentResponse, PaymentMethodCreate, 
    PaymentMethodResponse, PayoutCreate, PayoutResponse,
    TransactionResponse, PaymentStatistics
)
from app.services.payment_service import (
    create_payment, refund_payment, get_payment_by_id,
    get_booking_payment, get_client_payments, get_stylist_payments,
    add_payment_method, get_payment_methods, delete_payment_method,
    set_default_payment_method, create_payout, get_stylist_payouts,
    get_user_transactions, get_stylist_payment_statistics
)
from app.services.stylist_service import get_stylist_by_user_id

router = APIRouter()

@router.post("/", response_model=PaymentResponse)
async def create_new_payment(
    payment_in: PaymentCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new payment for a booking
    """
    payment = await create_payment(payment_in, str(current_user["_id"]))
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process payment"
        )
    
    return payment

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment details
    """
    payment = await get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if user has access to this payment
    user_id = str(current_user["_id"])
    if payment["clientId"] != user_id:
        # If not client, check if stylist
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or payment["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this payment"
            )
    
    return payment

@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_existing_payment(
    payment_id: str,
    reason: str = Body(None, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Refund a payment (admin or client only)
    """
    # Get payment
    payment = await get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if user has access to refund this payment
    user_id = str(current_user["_id"])
    if payment["clientId"] != user_id and not current_user.get("isAdmin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients or admins can refund payments"
        )
    
    refunded_payment = await refund_payment(payment_id, reason)
    if not refunded_payment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process refund"
        )
    
    return refunded_payment

@router.get("/booking/{booking_id}", response_model=PaymentResponse)
async def get_payment_for_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment for a booking
    """
    payment = await get_booking_payment(booking_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this booking"
        )
    
    # Check if user has access to this payment
    user_id = str(current_user["_id"])
    if payment["clientId"] != user_id:
        # If not client, check if stylist
        stylist = await get_stylist_by_user_id(user_id)
        if not stylist or payment["stylistId"] != str(stylist["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this payment"
            )
    
    return payment

@router.get("/client/me", response_model=List[PaymentResponse])
async def get_my_client_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get payments made by the current user as a client
    """
    payments = await get_client_payments(
        str(current_user["_id"]),
        skip=skip,
        limit=limit
    )
    
    return payments

@router.get("/stylist/me", response_model=List[PaymentResponse])
async def get_my_stylist_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get payments received by the current user as a stylist
    """
    # Get stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    payments = await get_stylist_payments(
        str(stylist["_id"]),
        skip=skip,
        limit=limit
    )
    
    return payments

@router.get("/statistics", response_model=PaymentStatistics)
async def get_payment_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment statistics for a stylist
    """
    # Get stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    statistics = await get_stylist_payment_statistics(str(stylist["_id"]))
    
    return statistics

@router.post("/methods", response_model=PaymentMethodResponse)
async def add_new_payment_method(
    method_in: PaymentMethodCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new payment method
    """
    # Ensure user is adding their own payment method
    if method_in.userId != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add payment methods for your own account"
        )
    
    method = await add_payment_method(method_in)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not add payment method"
        )
    
    return method

@router.get("/methods", response_model=List[PaymentMethodResponse])
async def get_user_payment_methods(
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment methods for the current user
    """
    methods = await get_payment_methods(str(current_user["_id"]))
    
    return methods

@router.delete("/methods/{method_id}", response_model=Dict[str, bool])
async def remove_payment_method(
    method_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a payment method
    """
    success = await delete_payment_method(method_id, str(current_user["_id"]))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    return {"success": success}

@router.put("/methods/{method_id}/default", response_model=Dict[str, bool])
async def make_default_payment_method(
    method_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Set a payment method as default
    """
    success = await set_default_payment_method(method_id, str(current_user["_id"]))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    return {"success": success}

@router.post("/payouts", response_model=PayoutResponse)
async def request_payout(
    payout_in: PayoutCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Request a payout for a stylist
    """
    # Get stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Ensure stylist is requesting payout for their own account
    if payout_in.stylistId != str(stylist["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only request payouts for your own account"
        )
    
    payout = await create_payout(payout_in)
    if not payout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process payout request"
        )
    
    return payout

@router.get("/payouts/stylist/me", response_model=List[PayoutResponse])
async def get_my_payouts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get payouts for the current user as a stylist
    """
    # Get stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    payouts = await get_stylist_payouts(
        str(stylist["_id"]),
        skip=skip,
        limit=limit
    )
    
    return payouts

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_my_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get transactions for the current user
    """
    transactions = await get_user_transactions(
        str(current_user["_id"]),
        skip=skip,
        limit=limit
    )
    
    return transactions
