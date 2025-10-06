from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any
from datetime import datetime

from app.core.auth import get_current_user
from app.schemas.favorite import FavoriteCreate, FavoriteResponse
from app.db.favorites import (
    add_favorite, 
    remove_favorite, 
    get_user_favorites,
    is_stylist_favorited,
    get_favorited_stylists_details
)
from app.services.stylist_service import get_stylist_by_id

router = APIRouter()

# Add or remove favorite endpoint
@router.post("/", response_model=FavoriteResponse)
async def manage_favorite(
    favorite_in: FavoriteCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Add or remove a stylist from user's favorites
    """
    user_id = str(current_user["_id"])
    stylist_id = favorite_in.stylistId
    
    # Verify stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Process based on the action
    if favorite_in.action == "add":
        result = await add_favorite(user_id, stylist_id)
        return result
    elif favorite_in.action == "remove":
        removed = await remove_favorite(user_id, stylist_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Favorite not found"
            )
        # Return a placeholder for consistency
        return {
            "_id": "removed",
            "userId": user_id,
            "stylistId": stylist_id,
            # Use current time to avoid None which could cause validation errors
            "createdAt": datetime.utcnow()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'add' or 'remove'"
        )


# Get user's favorite stylists
@router.get("/", response_model=Dict[str, Any])
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's favorite stylists with pagination
    
    Returns list of favorite stylists with full details
    """
    user_id = str(current_user["_id"])
    
    # Get favorited stylists with full details
    favorites = await get_favorited_stylists_details(user_id, skip, limit)
    return favorites


# Check if a stylist is in user's favorites
@router.get("/{stylist_id}", response_model=Dict[str, bool])
async def check_favorite_status(
    stylist_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a stylist is in user's favorites
    """
    user_id = str(current_user["_id"])
    
    # Check if the stylist exists first
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Check favorite status
    is_favorite = await is_stylist_favorited(user_id, stylist_id)
    
    return {"is_favorite": is_favorite}
