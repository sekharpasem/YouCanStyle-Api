from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from typing import List, Optional, Any, Dict
from app.core.auth import get_current_user
from app.schemas.stylist import StylistCreate, StylistUpdate, StylistResponse, StylistDocumentUpload, ApplicationStatus
from app.schemas.review import ReviewResponse
from app.services.stylist_service import (
    create_stylist, get_stylist_by_id, get_stylist_by_user_id, 
    update_stylist, get_all_stylists, update_portfolio,
    remove_portfolio_image, add_document, update_application_status,
    get_stylist_services, add_service, update_service, remove_service
)
from app.utils.file_upload import upload_file
from app.db.reviews import get_stylist_rating_and_review_count, get_reviews_by_stylist

router = APIRouter()

@router.post("/", response_model=StylistResponse)
async def create_stylist_profile(
    stylist_in: StylistCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new stylist profile for the current user
    """
    # Check if stylist profile already exists
    existing_stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if existing_stylist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stylist profile already exists for this user"
        )
    
    # Create stylist profile with user ID
    stylist_in.userId = str(current_user["_id"])
    stylist = await create_stylist(stylist_in)
    return stylist

@router.get("/me", response_model=StylistResponse)
async def get_my_stylist_profile(current_user: dict = Depends(get_current_user)):
    """
    Get the stylist profile of the current user
    """
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    return stylist

@router.get("/{stylist_id}", response_model=StylistResponse)
async def get_stylist(stylist_id: str):
    """
    Get a stylist profile by ID
    """
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    return stylist

@router.get("/{stylist_id}/rating", response_model=Dict[str, Any])
async def get_stylist_rating(stylist_id: str):
    """
    Get the average rating and review count for a specific stylist
    from the stylists_reviews collection
    """
    # Check if stylist exists first
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
        
    try:
        # Get rating and review count
        rating_data = await get_stylist_rating_and_review_count(stylist_id)
        return rating_data
    except Exception as e:
        # Handle any exceptions from the database layer
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stylist rating: {str(e)}"
        )

@router.get("/{stylist_id}/reviews", response_model=List[Dict[str, Any]])  # Using Dict instead of ReviewResponse due to field mapping differences
async def get_stylist_reviews(stylist_id: str, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """
    Get all reviews about a specific stylist from the stylists_reviews collection
    
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-100)
    """
    # Check if stylist exists first
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
        
    # Get all reviews by this stylist with pagination
    reviews = await get_reviews_by_stylist(stylist_id, skip=skip, limit=limit)
    return reviews

@router.put("/me", response_model=StylistResponse)
async def update_my_stylist_profile(
    stylist_update: StylistUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update the stylist profile of the current user
    """
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
        
    updated_stylist = await update_stylist(str(stylist["_id"]), stylist_update)
    return updated_stylist

@router.get("/", response_model=List[StylistResponse])
async def list_stylists(
    specialty: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rating: Optional[int] = None,
    online_only: Optional[bool] = None,
    in_person_only: Optional[bool] = None,
    is_intern: Optional[bool] = None,
    location: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """
    List all stylists with filters
    
    - **specialty**: Filter by stylist specialty area
    - **min_price/max_price**: Filter by price range
    - **rating**: Filter by minimum rating score
    - **online_only**: Show only stylists available for online sessions
    - **in_person_only**: Show only stylists available for in-person sessions
    - **is_intern**: Filter by stylist type (true for interns, false for professionals)
    - **location**: Filter by stylist location (case-insensitive partial match)
    - **skip/limit**: Pagination controls
    """
    stylists = await get_all_stylists(
        skip=skip,
        limit=limit,
        specialty=specialty,
        min_price=min_price,
        max_price=max_price,
        rating=rating,
        online_only=online_only,
        in_person_only=in_person_only,
        is_intern=is_intern,
        location=location
    )
    return stylists


@router.post("/me/portfolio", response_model=StylistResponse)
async def upload_portfolio_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an image to stylist's portfolio
    """
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Upload file to storage
    image_url = await upload_file(file, "portfolio")
    
    # Add image URL to portfolio
    await update_portfolio(str(stylist["_id"]), image_url)
    
    # Return updated stylist
    updated_stylist = await get_stylist_by_id(str(stylist["_id"]))
    return updated_stylist

@router.post("/me/documents", response_model=StylistResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_info: StylistDocumentUpload = Depends(),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a document (address proof or certificate)
    """
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Upload file to storage
    document_url = await upload_file(file, "documents")
    
    # Add document to stylist profile
    await add_document(
        str(stylist["_id"]), 
        document_info.documentType,
        document_url,
        document_info.certificateName
    )
    
    # Return updated stylist
    updated_stylist = await get_stylist_by_id(str(stylist["_id"]))
    return updated_stylist
