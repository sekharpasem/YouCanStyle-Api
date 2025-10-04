from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId

from app.db.mongodb import db
from app.schemas.review import ReviewCreate
from app.services.stylist_service import get_stylist_by_id
from app.services.user_service import get_user_by_id

async def create_review(review_in: ReviewCreate) -> Dict[str, Any]:
    """
    Create a new review for a stylist
    """
    # Ensure the stylist exists
    stylist = await get_stylist_by_id(review_in.stylistId)
    if not stylist:
        raise ValueError(f"Stylist with ID {review_in.stylistId} not found")

    # Create review data
    review_data = review_in.dict()
    
    # Set current time if not provided
    if not review_data.get("createdAt"):
        review_data["createdAt"] = datetime.utcnow()

    # Insert review into database
    result = await db.db.stylists_reviews.insert_one(review_data)
    
    # Get the created review
    review = await db.db.stylists_reviews.find_one({"_id": result.inserted_id})
    # Convert ObjectId to string for response validation
    if review and "_id" in review:
        review["_id"] = str(review["_id"])
    
    # Update stylist's average rating
    await update_stylist_rating(review_in.stylistId)
    
    return review

async def get_stylist_reviews(stylist_id: str) -> List[Dict[str, Any]]:
    """
    Get all reviews for a stylist
    """
    reviews = await db.db.stylists_reviews.find({"stylistId": stylist_id}).to_list(None)
    # Stringify ObjectIds for API response
    for r in reviews:
        if r.get("_id") is not None:
            r["_id"] = str(r["_id"])
    return reviews

async def update_stylist_rating(stylist_id: str) -> None:
    """
    Calculate and update the average rating for a stylist
    """
    # Aggregate average rating and count efficiently
    pipeline = [
        {"$match": {"stylistId": stylist_id}},
        {"$group": {"_id": None, "avgRating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    agg = await db.db.stylists_reviews.aggregate(pipeline).to_list(length=1)
    if not agg:
        # No reviews: set rating and count to zero
        result = await db.db.stylists.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$set": {"rating": 0.0, "reviewCount": 0}}
        )
        if result.modified_count == 0:
            # Fallback if stylist _id is stored as string in 'id'
            await db.db.stylists.update_one(
                {"id": stylist_id},
                {"$set": {"rating": 0.0, "reviewCount": 0}}
            )
        return
    avg = agg[0].get("avgRating") or 0.0
    count = agg[0].get("count", 0) or 0
    average_rating = round(float(avg), 1) if count > 0 else 0.0
    # Update stylist's rating and reviewCount
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$set": {"rating": average_rating, "reviewCount": int(count)}}
    )
    if result.modified_count == 0:
        # Fallback if stylist _id is stored as string in 'id'
        await db.db.stylists.update_one(
            {"id": stylist_id},
            {"$set": {"rating": average_rating, "reviewCount": int(count)}}
        )

async def delete_review(review_id: str) -> bool:
    """
    Delete a review by ID
    """
    # Get the review to find the stylist ID
    review = await db.db.stylists_reviews.find_one({"_id": ObjectId(review_id)})
    if not review:
        return False
    
    # Delete the review
    result = await db.db.stylists_reviews.delete_one({"_id": ObjectId(review_id)})
    
    # Update the stylist's average rating
    await update_stylist_rating(review["stylistId"])
    
    return result.deleted_count > 0
