from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from bson import ObjectId
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.review_service import create_review, get_stylist_reviews, delete_review
from app.db.mongodb import db

router = APIRouter()

@router.post("/", response_model=ReviewResponse)
async def add_review(
    review_in: ReviewCreate,
    current_user = Depends(get_current_user)
):
    """
    Add a new review for a stylist.
    """
    # Validate that the user is submitting their own review
    if review_in.userId != str(current_user["_id"]):
        raise HTTPException(
            status_code=403, 
            detail="You can only submit reviews as yourself"
        )
    
    try:
        review = await create_review(review_in)
        # Safety: ensure _id is a string for response validation
        if review and isinstance(review.get("_id"), (bytes, bytearray)):
            review["_id"] = review["_id"].decode()
        elif review and review.get("_id") is not None:
            review["_id"] = str(review["_id"])
        return review
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create review: {str(e)}")

@router.get("/stylist/{stylist_id}", response_model=List[ReviewResponse])
async def get_reviews_for_stylist(stylist_id: str):
    """
    Get all reviews for a specific stylist.
    """
    reviews = await get_stylist_reviews(stylist_id)
    return reviews

@router.delete("/{review_id}", status_code=204)
async def remove_review(review_id: str, current_user = Depends(get_current_user)):
    """
    Delete a review. Only the user who created the review or an admin can delete it.
    """
    # Get the review to check ownership
    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid review id")
    review = await db.db.stylists_reviews.find_one({"_id": oid})
    
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Check if the current user is the one who created the review or an admin
    if str(review.get("userId")) != str(current_user.get("_id")) and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="You can only delete your own reviews"
        )
    
    success = await delete_review(review_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete review")
