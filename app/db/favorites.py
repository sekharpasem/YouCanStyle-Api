from bson import ObjectId
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.db.mongodb import db


async def add_favorite(user_id: str, stylist_id: str) -> Dict[str, Any]:
    """
    Add a stylist to user's favorites
    """
    now = datetime.utcnow()
    favorite_data = {
        "userId": ObjectId(user_id),
        "stylistId": ObjectId(stylist_id),
        "createdAt": now
    }
    
    # Use upsert to either insert new document or do nothing if already exists
    result = await db.db.user_favorites.update_one(
        {"userId": ObjectId(user_id), "stylistId": ObjectId(stylist_id)},
        {"$set": favorite_data},
        upsert=True
    )
    
    if result.upserted_id:
        favorite_data["_id"] = result.upserted_id
    else:
        # If already existed, get the document
        doc = await db.db.user_favorites.find_one(
            {"userId": ObjectId(user_id), "stylistId": ObjectId(stylist_id)}
        )
        favorite_data["_id"] = doc["_id"]
    
    # Convert ObjectId to strings for JSON serialization
    serializable_data = {
        "_id": str(favorite_data["_id"]),
        "userId": str(favorite_data["userId"]),
        "stylistId": str(favorite_data["stylistId"]),
        "createdAt": favorite_data["createdAt"]
    }
    
    return serializable_data


async def remove_favorite(user_id: str, stylist_id: str) -> bool:
    """
    Remove a stylist from user's favorites
    """
    result = await db.db.user_favorites.delete_one(
        {"userId": ObjectId(user_id), "stylistId": ObjectId(stylist_id)}
    )
    
    return result.deleted_count > 0


async def get_user_favorites(user_id: str, skip: int = 0, limit: int = 20) -> Dict[str, Any]:
    """
    Get all favorites for a user with pagination
    """
    # Get total count for pagination
    total = await db.db.user_favorites.count_documents({"userId": ObjectId(user_id)})
    
    # Get favorites with pagination
    cursor = db.db.user_favorites.find({"userId": ObjectId(user_id)}) \
                          .sort("createdAt", -1) \
                          .skip(skip) \
                          .limit(limit)
    
    favorites = await cursor.to_list(length=limit)
    
    # Convert ObjectIds to strings for serialization
    for favorite in favorites:
        favorite["_id"] = str(favorite["_id"])
        favorite["userId"] = str(favorite["userId"])
        favorite["stylistId"] = str(favorite["stylistId"])
    
    return {
        "favorites": favorites,
        "total": total,
        "skip": skip,
        "limit": limit
    }


async def is_stylist_favorited(user_id: str, stylist_id: str) -> bool:
    """
    Check if a stylist is in user's favorites
    """
    count = await db.db.user_favorites.count_documents({
        "userId": ObjectId(user_id),
        "stylistId": ObjectId(stylist_id)
    })
    
    return count > 0


async def get_favorited_stylists_details(user_id: str, skip: int = 0, limit: int = 20) -> Dict[str, Any]:
    """
    Get full details of stylists favorited by a user
    
    This returns the complete stylist documents, not just the favorite relationships
    """
    # First get the favorite relationships with pagination
    favorites_data = await get_user_favorites(user_id, skip, limit)
    favorites = favorites_data["favorites"]
    
    # Extract stylist IDs
    stylist_ids = [ObjectId(fav["stylistId"]) for fav in favorites]
    
    # If no favorites, return early
    if not stylist_ids:
        return {
            "stylists": [],
            "total": 0,
            "skip": skip,
            "limit": limit
        }
    
    # Get the full stylist documents
    stylist_cursor = db.db.stylists.find({"_id": {"$in": stylist_ids}})
    stylists = await stylist_cursor.to_list(length=None)
    
    # Convert ObjectIds to strings
    for stylist in stylists:
        stylist["_id"] = str(stylist["_id"])
        if "userId" in stylist:
            stylist["userId"] = str(stylist["userId"])
    
    # Sort stylists to match the order of favorites
    # (which were sorted by createdAt)
    stylist_dict = {str(s["_id"]): s for s in stylists}
    ordered_stylists = [
        stylist_dict.get(fav["stylistId"]) 
        for fav in favorites
        if fav["stylistId"] in stylist_dict
    ]
    
    # Filter out any None values (in case a stylist was deleted but still favorited)
    ordered_stylists = [s for s in ordered_stylists if s is not None]
    
    return {
        "stylists": ordered_stylists,
        "total": favorites_data["total"],
        "skip": skip,
        "limit": limit
    }
