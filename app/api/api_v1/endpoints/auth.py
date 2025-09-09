from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import Any, Dict, Optional
from app.core.auth import create_access_token, get_current_user
from app.schemas.token import Token
from app.schemas.user import UserResponse, UserUpdate
from app.db.mongodb import db
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.config import settings
import random
import string

router = APIRouter()

# In-memory OTP storage (replace with Redis or database in production)
otp_store = {}

async def get_user_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get a user by phone number"""
    user = await db.db.users.find_one({"phone": phone})
    return user

async def create_user_with_phone(phone: str, fullName: str) -> Dict[str, Any]:
    """Create a new user with phone and name"""
    user_data = {
        "phone": phone,
        "fullName": fullName,
        "email": f"{phone.replace('+', '')}@placeholder.com",  # Placeholder email
        "role": "client",
        "isProfileComplete": False,
        "createdAt": datetime.utcnow(),
        "isActive": True,
        "settings": {
            "notifications": {
                "push": True,
                "sms": True
            },
            "preferredLanguage": "en",
            "darkMode": False
        }
    }
    
    result = await db.db.users.insert_one(user_data)
    created_user = await db.db.users.find_one({"_id": result.inserted_id})
    created_user["id"] = str(created_user["_id"])
    return created_user

@router.post("/request-otp")
async def request_otp(phone: str = Body(..., embed=True)) -> Any:
    """Request OTP for phone verification
    
    This endpoint is used to initiate the login/registration process.
    It checks if the user exists and sends an OTP to their phone.
    """
    # Check if user exists with this phone
    existing_user = await get_user_by_phone(phone)
    is_new_user = existing_user is None
    
    # Generate random 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))
    
    # Store OTP with expiration time (in production, use Redis with TTL)
    otp_store[phone] = otp
    
    # In production, send SMS here
    # sms_service.send(phone, f"Your OTP is {otp}")
    
    # For development, print OTP to console
    print(f"OTP for {phone}: {otp}")
    
    return {
        "isNewUser": is_new_user,
        "message": f"OTP sent to {phone}",
        "devOtp": otp  # Remove in production
    }

@router.post("/verify-otp")
async def verify_otp(
    phone: str = Body(...),
    otp: str = Body(...),
    fullName: Optional[str] = Body(None)
) -> Any:
    """Verify OTP and authenticate or register user
    
    This endpoint verifies the OTP and either logs in an existing user
    or registers a new user if the phone number is not found.
    """
    # Verify OTP
    stored_otp = otp_store.get(phone)
    if not stored_otp or stored_otp != otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # Clear used OTP
    if phone in otp_store:
        del otp_store[phone]
    
    # Check if user exists
    user = await get_user_by_phone(phone)
    
    if not user:
        # New user registration - fullName is optional
        name_to_use = fullName if fullName else f"User_{phone[-4:]}" # Use last 4 digits as default name
        
        # Create new user
        user = await create_user_with_phone(phone, name_to_use)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "phone": user["phone"],
            "fullName": user.get("fullName", ""),
            "isProfileComplete": user.get("isProfileComplete", False)
        }
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    # Transform MongoDB _id to id for Pydantic schema compatibility
    user_response = dict(current_user)
    user_response["id"] = str(user_response.pop("_id"))
    return user_response

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update current user profile"""
    from app.services.user_service import update_user
    
    user_id = str(current_user["_id"])
    updated_user = await update_user(user_id, user_update)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Transform MongoDB _id to id for Pydantic schema compatibility
    user_response = dict(updated_user)
    user_response["id"] = str(user_response.pop("_id"))
        
    return user_response
