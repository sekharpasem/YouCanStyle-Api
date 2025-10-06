from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from typing import List, Dict, Any
from app.core.auth import get_current_user
from app.schemas.stylist import Service
from app.db.mongodb import get_database
from app.services.stylist_service import (
    get_stylist_by_id, get_stylist_by_user_id,
    get_stylist_services, add_service, update_service, remove_service
)

router = APIRouter()

# Public catalog of static services (admin-managed)
@router.get("/", response_model=List[Dict[str, Any]])
async def list_services():
    """
    List all static services from the global 'services' collection.
    These are admin-provided, not stylist-specific.
    """
    db = await get_database()
    coll = db.get_collection("services")
    # Prefer active services first if the field exists
    cursor = coll.find({}).sort([("category", 1), ("name", 1)])
    services: List[Dict[str, Any]] = []
    async for doc in cursor:
        # Normalize id field
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        services.append(doc)
    return services

@router.get("/{stylist_id}", response_model=List[Dict[str, Any]])
@router.get("/{stylist_id}/", response_model=List[Dict[str, Any]])
async def get_services_by_stylist(stylist_id: str):
    """
    Get all services offered by a stylist
    """
    # First check if stylist exists
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist not found"
        )
    
    # Get the services for this stylist
    services = await get_stylist_services(stylist_id)
    return services

@router.get("/me", response_model=List[Dict[str, Any]])
@router.get("/me/", response_model=List[Dict[str, Any]])
async def get_my_services(current_user: dict = Depends(get_current_user)):
    """
    Get all services offered by the current stylist
    """
    # Get current stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Get the services
    services = await get_stylist_services(str(stylist["_id"]))
    return services

@router.post("/me", response_model=Dict[str, Any])
@router.post("/me/", response_model=Dict[str, Any])
async def add_stylist_service(
    service: Service,
    current_user: dict = Depends(get_current_user)
):
    """
    Add a new service to the current stylist's offerings
    """
    # Get current stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Add the service (ensure enum fields are serialized)
    payload = jsonable_encoder(service)
    success = await add_service(str(stylist["_id"]), payload)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add service"
        )
    
    # Return the updated services
    services = await get_stylist_services(str(stylist["_id"]))
    return {"message": "Service added successfully", "services": services}

@router.put("/me/{service_id}", response_model=Dict[str, Any])
@router.put("/me/{service_id}/", response_model=Dict[str, Any])
async def update_stylist_service(
    service_id: str,
    service: Service,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing service for the current stylist
    """
    # Get current stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Update the service (ensure enum fields are serialized)
    payload = jsonable_encoder(service)
    success = await update_service(str(stylist["_id"]), service_id, payload)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or update failed"
        )
    
    # Return the updated services
    services = await get_stylist_services(str(stylist["_id"]))
    return {"message": "Service updated successfully", "services": services}

@router.delete("/me/{service_id}", response_model=Dict[str, Any])
@router.delete("/me/{service_id}/", response_model=Dict[str, Any])
async def delete_stylist_service(
    service_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a service from the current stylist's offerings
    """
    # Get current stylist profile
    stylist = await get_stylist_by_user_id(str(current_user["_id"]))
    if not stylist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stylist profile not found"
        )
    
    # Remove the service
    success = await remove_service(str(stylist["_id"]), service_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or delete failed"
        )
    
    # Return the updated services
    services = await get_stylist_services(str(stylist["_id"]))
    return {"message": "Service deleted successfully", "services": services}
