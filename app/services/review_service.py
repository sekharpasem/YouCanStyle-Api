from datetime import datetime
from typing import Dict, Any, List

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
    result = await db.db.stylist_reviews.insert_one(review_data)
    
    # Get the created review
    review = await db.db.stylist_reviews.find_one({"_id": result.inserted_id})
    
    # Update stylist's average rating
    await update_stylist_rating(review_in.stylistId)
    
    return review

async def get_stylist_reviews(stylist_id: str) -> List[Dict[str, Any]]:
    """
    Get all reviews for a stylist
    """
    reviews = await db.stylist_reviews.find({"stylistId": stylist_id}).to_list(None)
    return reviews

async def update_stylist_rating(stylist_id: str) -> None:
    """
    Calculate and update the average rating for a stylist
    """
    # Get all reviews for the stylist
    reviews = await db.stylist_reviews.find({"stylistId": stylist_id}).to_list(None)
    
    if not reviews:
        return
    
    # Calculate average rating
    total_rating = sum(review["rating"] for review in reviews)
    average_rating = round(total_rating / len(reviews), 1)
    
    # Update stylist's rating
    await db.stylists.update_one(
        {"_id": stylist_id},
        {"$set": {"rating": average_rating, "reviewCount": len(reviews)}}
    )

async def delete_review(review_id: str) -> bool:
    """
    Delete a review by ID
    """
    # Get the review to find the stylist ID
    review = await db.stylist_reviews.find_one({"_id": review_id})
    if not review:
        return False
    
    # Delete the review
    result = await db.stylist_reviews.delete_one({"_id": review_id})
    
    # Update the stylist's average rating
    await update_stylist_rating(review["stylistId"])
    
    return result.deleted_count > 0
