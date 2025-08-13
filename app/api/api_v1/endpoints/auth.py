from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any
from app.core.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import create_user, get_user_by_email
from datetime import timedelta
from app.core.config import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate) -> Any:
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists."
        )
    
    # Create new user
    user = await create_user(user_in)
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """Login and get access token."""
    user = await get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.get("password")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/verify-otp", response_model=Token)
async def verify_otp(phone: str, otp: str) -> Any:
    """Verify OTP and generate token for phone login."""
    # In a real implementation, verify OTP against stored value
    # This is a placeholder implementation
    # Normally, you would fetch the user by phone number and validate OTP
    
    # Simulate OTP verification (always successful for demo)
    # In production, implement proper OTP verification
    
    # Create access token after successful verification
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": phone}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
