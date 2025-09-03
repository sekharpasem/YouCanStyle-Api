from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import Any, Dict, Optional
from app.core.auth import create_access_token, get_current_user
from app.schemas.token import Token
from app.schemas.stylist import StylistResponse, StylistUpdate
from app.db.mongodb import db
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.config import settings
import random
import string

router = APIRouter()

# In-memory OTP storage (replace with Redis or database in production)
stylist_otp_store = {}

async def get_stylist_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get a stylist by phone number"""
    stylist = await db.db.stylists.find_one({"phone": phone})
    return stylist

async def create_stylist_with_phone(phone: str, fullName: str) -> Dict[str, Any]:
    """Create a new stylist with phone and name"""
    stylist_data = {
        "phone": phone,
        "name": fullName,
        "email": f"{phone.replace('+', '')}@placeholder.com",  # Placeholder email
        "isIntern": False,
        "location": "",
        "rating": 0.0,
        "reviewCount": 0,
        "price": 0.0,
        "profileImage": "",
        "specialties": [],
        "isProfileComplete": False,
        "availableOnline": True,
        "availableInPerson": True,
        "applicationStatus": "pending",  # Initial status
        "createdAt": datetime.utcnow(),
        "isActive": True,
        "userId": None,  # Will be linked to a user account if exists
        "services": [],
        "documents": [],
        "portfolioImages": []
    }
    
    result = await db.db.stylists.insert_one(stylist_data)
    created_stylist = await db.db.stylists.find_one({"_id": result.inserted_id})
    created_stylist["id"] = str(created_stylist["_id"])
    return created_stylist

@router.post("/request-otp")
async def request_stylist_otp(phone: str = Body(..., embed=True)) -> Any:
    """Request OTP for stylist phone verification
    
    This endpoint is used to initiate the login/registration process for stylists.
    It checks if the stylist exists and sends an OTP to their phone.
    """
    # Check if stylist exists with this phone
    existing_stylist = await get_stylist_by_phone(phone)
    is_new_stylist = existing_stylist is None
    
    # Generate random 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store OTP with expiration time (in production, use Redis with TTL)
    stylist_otp_store[phone] = otp
    
    # In production, send SMS here
    # sms_service.send(phone, f"Your OTP is {otp}")
    
    # For development, print OTP to console
    print(f"Stylist OTP for {phone}: {otp}")
    
    return {
        "isNewStylist": is_new_stylist,
        "message": f"OTP sent to {phone}",
        "devOtp": otp  # Remove in production
    }

@router.post("/verify-otp")
async def verify_stylist_otp(
    phone: str = Body(...),
    otp: str = Body(...),
    fullName: Optional[str] = Body(None)
) -> Any:
    """Verify OTP and authenticate or register stylist
    
    This endpoint verifies the OTP and either logs in an existing stylist
    or registers a new stylist if the phone number is not found.
    """
    # Verify OTP
    stored_otp = stylist_otp_store.get(phone)
    if not stored_otp or stored_otp != otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # Clear used OTP
    if phone in stylist_otp_store:
        del stylist_otp_store[phone]
    
    # Check if stylist exists
    stylist = await get_stylist_by_phone(phone)
    
    if not stylist:
        # New stylist registration - fullName is required for stylists
        if not fullName:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Full name is required for new stylist registration"
            )
        
        # Create new stylist
        stylist = await create_stylist_with_phone(phone, fullName)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(stylist["_id"]), "role": "stylist"}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "stylist": {
            "id": str(stylist["_id"]),
            "phone": stylist["phone"],
            "name": stylist.get("name", ""),
            "isProfileComplete": stylist.get("isProfileComplete", False),
            "applicationStatus": stylist.get("applicationStatus", "pending")
        }
    }

@router.get("/me", response_model=StylistResponse)
async def read_stylist_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current stylist profile"""
    # Verify the user is a stylist
    stylist = await db.db.stylists.find_one({"_id": ObjectId(current_user["_id"])})
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    return stylist

@router.put("/me", response_model=StylistResponse)
async def update_stylist_profile(
    stylist_update: StylistUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update current stylist profile"""
    from app.services.stylist_service import update_stylist
    
    stylist_id = str(current_user["_id"])
    updated_stylist = await update_stylist(stylist_id, stylist_update)
    
    if not updated_stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
        
    return updated_stylist
