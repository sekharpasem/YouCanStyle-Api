from bson import ObjectId
from datetime import datetime
from typing import Dict, List, Optional, Any
from pymongo import DESCENDING

from app.db.mongodb import db

async def create_user_review(user_id: str, stylist_id: str, review: str, rating: int, created_at: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Create a new review from user to stylist
    """
    if created_at is None:
        created_at = datetime.utcnow()
        
    review_data = {
        "userId": ObjectId(user_id),
        "stylistId": ObjectId(stylist_id),
        "review": review,
        "rating": rating,
        "createdAt": created_at
    }
    
    result = await db.db.users_reviews.insert_one(review_data)
    review_data["_id"] = result.inserted_id
    return review_data

async def get_stylist_reviews(stylist_id: str) -> List[Dict[str, Any]]:
    """
    Get all reviews for a specific stylist
    """
    reviews = await db.db.users_reviews.find({"stylistId": ObjectId(stylist_id)}).sort("createdAt", DESCENDING).to_list(length=None)
    return reviews

async def create_stylist_review(stylist_id: str, user_id: str, review: str, rating: int, created_at: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Create a new review from stylist to user
    """
    if created_at is None:
        created_at = datetime.utcnow()
        
    review_data = {
        "stylistId": ObjectId(stylist_id),
        "userId": ObjectId(user_id),
        "review": review,
        "rating": rating,
        "createdAt": created_at
    }
    
    result = await db.db.stylists_reviews.insert_one(review_data)
    review_data["_id"] = result.inserted_id
    return review_data

async def get_user_reviews(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all reviews for a specific user from stylists
    """
    reviews = await db.db.stylists_reviews.find({"userId": ObjectId(user_id)}).sort("createdAt", DESCENDING).to_list(length=None)
    return reviews

async def get_stylist_rating_and_review_count(stylist_id: str) -> Dict[str, Any]:
    """
    Get the average rating and review count for a specific stylist from the stylists_reviews collection
    """
    try:
        # Check if collection exists and create it if needed
        collections = await db.db.list_collection_names()
        if "stylists_reviews" not in collections:
            # If collection doesn't exist yet, create it by inserting and then removing a dummy document
            dummy_doc = {"_id": "temp", "temp": True}
            await db.db.stylists_reviews.insert_one(dummy_doc)
            await db.db.stylists_reviews.delete_one({"_id": "temp"})
            # Return default values since there are no reviews yet
            return {
                "stylistId": str(stylist_id),
                "rating": 0.0,
                "reviewCount": 0
            }
            
        # Proceed with aggregation
        pipeline = [
            {"$match": {"stylistId": ObjectId(stylist_id)}},
            {"$group": {
                "_id": "$stylistId",
                "averageRating": {"$avg": "$rating"},
                "reviewCount": {"$sum": 1}
            }}
        ]
        
        result = await db.db.stylists_reviews.aggregate(pipeline).to_list(length=1)
        
        if result:
            return {
                "stylistId": str(stylist_id),
                "rating": round(result[0]["averageRating"], 1),
                "reviewCount": result[0]["reviewCount"]
            }
        else:
            return {
                "stylistId": str(stylist_id),
                "rating": 0.0,
                "reviewCount": 0
            }
    except Exception as e:
        # If any error occurs, return default values
        print(f"Error getting stylist rating: {e}")
        return {
            "stylistId": str(stylist_id),
            "rating": 0.0,
            "reviewCount": 0
        }
