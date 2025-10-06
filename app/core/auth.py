from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.db.mongodb import db
from bson.objectid import ObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user from token.

    Supports two token shapes:
    - Client/user tokens: { sub: <users._id>, ... }
    - Stylist tokens: { sub: <stylists._id>, role: "stylist", ... }

    For stylist tokens we return a minimal user-like dict where `_id` is set to the
    stylist's `userId` (phone). This keeps downstream code (which calls
    `get_stylist_by_user_id(current_user["_id"])`) working without changes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        subject: str = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if subject is None:
            raise credentials_exception
    except JWTError as jwt_error:
        print(f"JWT decode error: {jwt_error}")
        raise credentials_exception
    
    # Add explicit error handling for ObjectId conversion
    # If stylist token, resolve stylist and return a minimal user-like dict
    if role == "stylist":
        try:
            stylist_oid = ObjectId(subject)
        except Exception as e:
            print(f"Invalid stylist ObjectId format in token: {subject}, Error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid stylist ID format in token"
            )

        try:
            stylist = await db.db.stylists.find_one({"_id": stylist_oid})
            if stylist is None:
                print(f"Stylist not found for ID: {subject}")
                raise credentials_exception
            # Return a minimal user-like object with _id equal to stylist.userId (phone)
            return {
                "_id": stylist.get("userId"),
                "role": "stylist",
            }
        except HTTPException:
            raise
        except Exception as db_error:
            print(f"Stylist DB error: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving stylist data"
            )

    # Default: treat as client/user token (subject is users._id)
    try:
        object_id = ObjectId(subject)
    except Exception as e:
        print(f"Invalid ObjectId format: {subject}, Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format in token"
        )

    try:
        user = await db.db.users.find_one({"_id": object_id})
        if user is None:
            print(f"User not found for ID: {subject}")
            raise credentials_exception
    except HTTPException:
        raise
    except Exception as db_error:
        print(f"Database error: {db_error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user data"
        )

    return user
