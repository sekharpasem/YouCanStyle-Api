from typing import Dict, Any, Optional
from app.db.mongodb import db
from app.schemas.user import UserCreate, UserUpdate
from app.core.auth import get_password_hash
from datetime import datetime
from bson import ObjectId

async def create_user(user_in: UserCreate) -> Dict[str, Any]:
    """
    Create a new user in the database
    """
    # Create user with hashed password
    user_data = user_in.dict()
    user_data["password"] = get_password_hash(user_data["password"])
    user_data["createdAt"] = datetime.utcnow()
    user_data["isActive"] = True
    user_data["settings"] = {
        "notifications": {
            "email": True,
            "push": True,
            "sms": True
        },
        "preferredLanguage": "en",
        "darkMode": False
    }

    # Insert user into database
    result = await db.db.users.insert_one(user_data)
    
    # Get the created user
    created_user = await db.db.users.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_user["id"] = str(created_user["_id"])
    
    return created_user

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by email
    """
    user = await db.db.users.find_one({"email": email})
    return user

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID
    """
    try:
        user = await db.db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["id"] = str(user["_id"])
        return user
    except:
        return None

async def update_user(user_id: str, user_update: UserUpdate) -> Optional[Dict[str, Any]]:
    """
    Update a user
    """
    # Get the current user
    user = await get_user_by_id(user_id)
    if not user:
        return None
        
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    
    if update_data:
        # Add updated timestamp
        update_data["updatedAt"] = datetime.utcnow()
        
        # Update user in database
        await db.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
    # Get the updated user
    updated_user = await get_user_by_id(user_id)
    return updated_user

async def update_last_login(user_id: str) -> None:
    """
    Update user's last login timestamp
    """
    await db.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"lastLogin": datetime.utcnow()}}
    )

async def deactivate_user(user_id: str) -> bool:
    """
    Deactivate a user
    """
    result = await db.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"isActive": False}}
    )
    return result.modified_count > 0
