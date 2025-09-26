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
    Get all reviews for a specific stylist from users
    """
    reviews = await db.db.users_reviews.find({"stylistId": ObjectId(stylist_id)}).sort("createdAt", DESCENDING).to_list(length=None)
    return reviews

async def get_reviews_by_stylist(stylist_id: str, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get all reviews about a specific stylist from the stylists_reviews collection
    with pagination support
    
    Args:
        stylist_id: ID of the stylist being reviewed
        skip: Number of records to skip
        limit: Maximum number of records to return
    """
    # Convert string ID to ObjectId for MongoDB query
    stylist_object_id = ObjectId(stylist_id)
    
    # Find reviews where this stylist is being reviewed
    cursor = db.db.stylists_reviews.find({"stylistId": stylist_id})\
                               .sort("createdAt", DESCENDING)\
                               .skip(skip)\
                               .limit(limit)
    
    reviews = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for JSON serialization
    for review in reviews:
        review["_id"] = str(review["_id"])
        review["stylistId"] = str(review["stylistId"])
        review["userId"] = str(review["userId"])
        # Ensure createdAt is serializable
        if isinstance(review.get("createdAt"), datetime):
            review["createdAt"] = review["createdAt"].isoformat()
    
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
    
    Args:
        stylist_id: ID of the stylist to get rating for
    """
    try:
        # Convert string ID to ObjectId for MongoDB query
        stylist_object_id = stylist_id
            
        # Set up the aggregation pipeline to calculate average rating and count reviews
        pipeline = [
            {"$match": {"stylistId": stylist_object_id}},  # Find all reviews for this stylist
            {"$group": {
                "_id": "$stylistId",                  # Group by stylist ID
                "averageRating": {"$avg": "$rating"},  # Calculate average rating
                "reviewCount": {"$sum": 1}             # Count total number of reviews
            }}
        ]
        
        # Execute the aggregation pipeline
        result = await db.db.stylists_reviews.aggregate(pipeline).to_list(length=1)
        
        # Process the results
        if result:
            # Reviews found - return actual data
            return {
                "stylistId": str(stylist_id),
                "rating": round(result[0]["averageRating"], 1),  # Round to 1 decimal place
                "reviewCount": result[0]["reviewCount"]
            }
        else:
            # No reviews found - return zeros (this is actual data, not default)
            return {
                "stylistId": str(stylist_id),
                "rating": 0.0,
                "reviewCount": 0
            }
    except Exception as e:
        # Log the error and re-raise it for proper handling in the API layer
        print(f"Error getting stylist rating: {e}")
        raise
