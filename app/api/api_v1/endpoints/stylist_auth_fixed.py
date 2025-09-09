from fastapi import APIRouter, HTTPException, status, Body
from typing import Any, Dict, Optional
from app.core.auth import create_access_token
from app.schemas.token import Token
from app.db.mongodb import db
from bson import ObjectId
from datetime import datetime, timedelta
from app.core.config import settings
import random
import string
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory OTP storage for stylists (replace with Redis or database in production)
stylist_otp_store = {}

async def get_stylist_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Get a stylist by phone number"""
    try:
        # Use userId instead of phone as phone isn't in the schema
        # Assuming userId could be a phone number in some cases
        stylist = await db.stylists.find_one({"userId": phone})
        return stylist
    except Exception as e:
        logger.error(f"Error getting stylist by phone: {e}")
        return None

async def create_temporary_stylist(phone: str) -> Dict[str, Any]:
    """Create a temporary stylist account with minimal details"""
    try:
        # Generate an ObjectId for the stylist
        stylist_id = ObjectId()
        
        # Create stylist data according to the schema
        stylist_data = {
            "_id": stylist_id,
            "userId": phone,  # Using phone as userId for now
            "name": f"Stylist_{phone[-4:]}",  # Use last 4 digits of phone as identifier
            "isIntern": True,  # Start as intern by default
            "location": "",
            "bio": "",
            "portfolioImages": [],
            "specialties": [],
            "price": 0.0,
            "rating": 0.0,
            "reviewCount": 0,
            "availableOnline": False,
            "availableInPerson": False,
            "experience": {
                "years": 0,
                "previousEmployers": [],
                "education": []
            },
            "services": [],
            "documents": {},
            "applicationStatus": "pending",
            "availabilitySchedule": {
                "monday": {"slots": []},
                "tuesday": {"slots": []},
                "wednesday": {"slots": []},
                "thursday": {"slots": []},
                "friday": {"slots": []},
                "saturday": {"slots": []},
                "sunday": {"slots": []}
            },
            "unavailable": [],
            "createdAt": datetime.utcnow()
        }
        
        result = await db.stylists.insert_one(stylist_data)
        created_stylist = await db.stylists.find_one({"_id": result.inserted_id})
        created_stylist["id"] = str(created_stylist["_id"])
        return created_stylist
    except Exception as e:
        logger.error(f"Error creating temporary stylist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create temporary stylist: {str(e)}"
        )

@router.post("/stylist/request-otp")
async def request_stylist_otp(phone: str = Body(..., embed=True)) -> Any:
    """Request OTP for stylist phone verification
    
    This endpoint is used to initiate the stylist login/registration process.
    It checks if the stylist exists and sends an OTP to their phone.
    """
    try:
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
        logger.info(f"Stylist OTP for {phone}: {otp}")
        
        return {
            "isNewStylist": is_new_stylist,
            "message": f"OTP sent to {phone}",
            "devOtp": otp  # Remove in production
        }
    except Exception as e:
        logger.error(f"Error in request_stylist_otp: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OTP request"
        )

@router.post("/stylist/verify-otp")
async def verify_stylist_otp(
    phone: str = Body(...),
    otp: str = Body(...)
) -> Any:
    """Verify OTP and authenticate or register stylist
    
    This endpoint verifies the OTP and either logs in an existing stylist
    or creates a temporary stylist account if the phone number is not found.
    """
    try:
        logger.info(f"Verifying OTP for phone: {phone}")
        logger.debug(f"Current OTP store: {stylist_otp_store}")
        
        # Verify OTP
        stored_otp = stylist_otp_store.get(phone)
        if not stored_otp:
            logger.warning(f"No OTP found for phone: {phone}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not requested"
            )
            
        if stored_otp != otp:
            logger.warning(f"Invalid OTP for phone: {phone}. Expected: {stored_otp}, Received: {otp}")
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
            # Create new temporary stylist account
            logger.info(f"Creating new temporary stylist for phone: {phone}")
            stylist = await create_temporary_stylist(phone)
        
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
                "userId": stylist["userId"],
                "name": stylist.get("name", f"Stylist_{phone[-4:]}"),
                "applicationStatus": stylist.get("applicationStatus", "pending"),
                "isProfileComplete": False
            }
        }
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Error in verify_stylist_otp: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred during OTP verification"
        )
