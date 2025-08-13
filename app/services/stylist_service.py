from typing import Dict, Any, List, Optional
from app.db.mongodb import db
from app.schemas.stylist import StylistCreate, StylistUpdate, ApplicationStatus
from datetime import datetime
from bson import ObjectId

async def create_stylist(stylist_in: StylistCreate) -> Dict[str, Any]:
    """
    Create a new stylist profile
    """
    stylist_data = stylist_in.dict()
    stylist_data["createdAt"] = datetime.utcnow()
    stylist_data["rating"] = 0
    stylist_data["reviewCount"] = 0
    stylist_data["isIntern"] = False
    stylist_data["portfolioImages"] = []
    stylist_data["documents"] = {
        "addressProof": {
            "url": "",
            "verified": False
        },
        "certificates": []
    }
    stylist_data["applicationStatus"] = ApplicationStatus.PENDING
    stylist_data["availabilitySchedule"] = {
        "monday": {"slots": []},
        "tuesday": {"slots": []},
        "wednesday": {"slots": []},
        "thursday": {"slots": []},
        "friday": {"slots": []},
        "saturday": {"slots": []},
        "sunday": {"slots": []}
    }
    stylist_data["earnings"] = {
        "total": 0,
        "pending": 0,
        "withdrawn": 0
    }

    # Insert stylist into database
    result = await db.db.stylists.insert_one(stylist_data)
    
    # Get the created stylist
    created_stylist = await db.db.stylists.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_stylist["id"] = str(created_stylist["_id"])
    
    return created_stylist

async def get_stylist_by_id(stylist_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a stylist by ID
    """
    try:
        stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)})
        if stylist:
            stylist["id"] = str(stylist["_id"])
        return stylist
    except:
        return None

async def get_stylist_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a stylist by user ID
    """
    stylist = await db.db.stylists.find_one({"userId": user_id})
    if stylist:
        stylist["id"] = str(stylist["_id"])
    return stylist

async def update_stylist(stylist_id: str, stylist_update: StylistUpdate) -> Optional[Dict[str, Any]]:
    """
    Update a stylist
    """
    # Get the current stylist
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        return None
        
    # Update only provided fields
    update_data = stylist_update.dict(exclude_unset=True)
    
    if update_data:
        # Add updated timestamp
        update_data["updatedAt"] = datetime.utcnow()
        
        # Update stylist in database
        await db.db.stylists.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$set": update_data}
        )
        
    # Get the updated stylist
    updated_stylist = await get_stylist_by_id(stylist_id)
    return updated_stylist

async def get_all_stylists(
    skip: int = 0, 
    limit: int = 10,
    specialty: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rating: Optional[int] = None,
    online_only: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Get all stylists with filtering options
    """
    # Build query
    query = {"applicationStatus": ApplicationStatus.APPROVED}
    
    if specialty:
        query["specialties"] = specialty
    
    if min_price is not None and max_price is not None:
        query["price"] = {"$gte": min_price, "$lte": max_price}
    elif min_price is not None:
        query["price"] = {"$gte": min_price}
    elif max_price is not None:
        query["price"] = {"$lte": max_price}
        
    if rating is not None:
        query["rating"] = {"$gte": rating}
        
    if online_only is not None and online_only:
        query["availableOnline"] = True
    
    # Execute query
    cursor = db.db.stylists.find(query).skip(skip).limit(limit).sort("rating", -1)
    stylists = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for stylist in stylists:
        stylist["id"] = str(stylist["_id"])
        
    return stylists

async def update_portfolio(stylist_id: str, image_url: str) -> bool:
    """
    Add an image to stylist's portfolio
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$push": {"portfolioImages": image_url}}
    )
    return result.modified_count > 0

async def remove_portfolio_image(stylist_id: str, image_url: str) -> bool:
    """
    Remove an image from stylist's portfolio
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$pull": {"portfolioImages": image_url}}
    )
    return result.modified_count > 0

async def add_document(
    stylist_id: str, 
    document_type: str, 
    url: str, 
    certificate_name: Optional[str] = None
) -> bool:
    """
    Add a document (address proof or certificate)
    """
    if document_type == "addressProof":
        result = await db.db.stylists.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$set": {"documents.addressProof": {"url": url, "verified": False}}}
        )
    elif document_type == "certificate":
        if not certificate_name:
            certificate_name = "Certificate"
            
        result = await db.db.stylists.update_one(
            {"_id": ObjectId(stylist_id)},
            {"$push": {"documents.certificates": {
                "name": certificate_name,
                "url": url,
                "verified": False
            }}}
        )
    else:
        return False
        
    return result.modified_count > 0

async def update_application_status(stylist_id: str, status: ApplicationStatus) -> bool:
    """
    Update stylist application status
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$set": {"applicationStatus": status}}
    )
    return result.modified_count > 0

async def update_earnings(stylist_id: str, amount: float) -> bool:
    """
    Update stylist earnings (add to total and pending)
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {
            "$inc": {
                "earnings.total": amount,
                "earnings.pending": amount
            }
        }
    )
    return result.modified_count > 0
