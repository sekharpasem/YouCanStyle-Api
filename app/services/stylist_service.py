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
    # Ensure profileImage is present (empty by default)
    if not stylist_data.get("profileImage"):
        stylist_data["profileImage"] = ""
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

    # Normalize services: ensure each has a valid 'type'
    if stylist_data.get("services"):
        normalized_services = []
        for svc in stylist_data["services"]:
            s = dict(svc)
            t = str(s.get("type", "online")).lower()
            s["type"] = "inperson" if t == "inperson" else "online"
            normalized_services.append(s)
        stylist_data["services"] = normalized_services

    # Compute initial price as min of services if available
    try:
        prices = [float(s.get("price", 0)) for s in stylist_data.get("services", []) if s and s.get("isActive", True) and s.get("price") is not None]
        min_price = float(min(prices)) if prices else float(stylist_data.get("price", 0))
        stylist_data["price"] = min_price
    except Exception:
        stylist_data["price"] = float(stylist_data.get("price", 0))

    # Generate an ObjectId and assign it as _id
    stylist_id = ObjectId()
    stylist_data["_id"] = stylist_id
    
    # Also add the string representation as id to avoid duplicate key error
    stylist_data["id"] = str(stylist_id)
    
    # Insert stylist into database
    result = await db.db.stylists.insert_one(stylist_data)
    
    # Get the created stylist
    created_stylist = await db.db.stylists.find_one({"_id": result.inserted_id})
    if created_stylist is not None:
        created_stylist["id"] = str(created_stylist["_id"])  # ensure id string
        created_stylist.setdefault("portfolioImages", [])
        created_stylist.setdefault("profileImage", "")
    
    return created_stylist

async def get_stylist_by_id(stylist_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a stylist by ID
    """
    try:
        stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)})
        if stylist:
            stylist["id"] = str(stylist["_id"])
            stylist.setdefault("portfolioImages", [])
            stylist.setdefault("profileImage", "")
            # Ensure price reflects min of services
            try:
                prices = [float(s.get("price", 0)) for s in stylist.get("services", []) if s and s.get("isActive", True) and s.get("price") is not None]
                computed_min = float(min(prices)) if prices else float(stylist.get("price", 0))
                current_price = float(stylist.get("price", 0))
                if abs(current_price - computed_min) > 1e-6:
                    await db.db.stylists.update_one({"_id": ObjectId(stylist_id)}, {"$set": {"price": computed_min}})
                    stylist["price"] = computed_min
            except Exception:
                pass
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
        stylist.setdefault("portfolioImages", [])
        stylist.setdefault("profileImage", "")
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
    online_only: Optional[bool] = None,
    in_person_only: Optional[bool] = None,
    is_intern: Optional[bool] = None,
    location: Optional[str] = None
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
        
    # Handle online and in-person availability filters
    if online_only is not None:
        query["availableOnline"] = online_only
        
    if in_person_only is not None:
        query["availableInPerson"] = in_person_only
    
    # By default, exclude stylists who are unavailable in both modes
    # Apply this only when no explicit availability filter is requested
    if online_only is None and in_person_only is None:
        query["$or"] = [{"availableOnline": True}, {"availableInPerson": True}]
    
    # Filter by stylist type (intern or professional)
    if is_intern is not None:
        query["isIntern"] = is_intern
    
    # Location filtering - case insensitive partial match
    if location is not None and location.strip():
        query["location"] = {"$regex": location, "$options": "i"}
    
    # Execute query
    cursor = db.db.stylists.find(query).skip(skip).limit(limit).sort("rating", -1)
    stylists = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for stylist in stylists:
        stylist["id"] = str(stylist["_id"])
        stylist.setdefault("portfolioImages", [])
        stylist.setdefault("profileImage", "")
        # Keep price as min of services for response and try to reconcile stored value
        try:
            prices = [float(s.get("price", 0)) for s in stylist.get("services", []) if s and s.get("isActive", True) and s.get("price") is not None]
            computed_min = float(min(prices)) if prices else float(stylist.get("price", 0))
            current_price = float(stylist.get("price", 0))
            stylist["price"] = computed_min
            if abs(current_price - computed_min) > 1e-6:
                await db.db.stylists.update_one({"_id": stylist["_id"]}, {"$set": {"price": computed_min}})
        except Exception:
            pass
        
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

async def set_profile_image(stylist_id: str, image_url: str) -> bool:
    """
    Set or update the main profile image URL for a stylist
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$set": {"profileImage": image_url}}
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

async def get_stylist_services(stylist_id: str) -> List[Dict[str, Any]]:
    """
    Get services offered by a stylist
    """
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        return []
    return stylist.get("services", [])

async def add_service(stylist_id: str, service_data: Dict[str, Any]) -> bool:
    """
    Add a new service to stylist's offerings
    """
    # Add a unique ID to the service
    service = dict(service_data)
    service["id"] = str(ObjectId())
    service["createdAt"] = datetime.utcnow()
    # Normalize type
    t = str(service.get("type", "online")).lower()
    service["type"] = "inperson" if t == "inperson" else "online"

    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$push": {"services": service}}
    )
    # Recompute min price
    if result.modified_count > 0:
        try:
            stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)}, {"services": 1})
            prices = [float(s.get("price", 0)) for s in (stylist.get("services", []) if stylist else []) if s and s.get("isActive", True) and s.get("price") is not None]
            min_price = float(min(prices)) if prices else 0.0
            await db.db.stylists.update_one({"_id": ObjectId(stylist_id)}, {"$set": {"price": min_price}})
        except Exception:
            pass
    return result.modified_count > 0

async def update_service(stylist_id: str, service_id: str, service_data: Dict[str, Any]) -> bool:
    """
    Update an existing service for a stylist
    """
    # Update with timestamp and merge existing service to avoid dropping fields
    service_data = dict(service_data)
    service_data["updatedAt"] = datetime.utcnow()

    # Fetch current service
    stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id), "services.id": service_id}, {"services.$": 1})
    current = None
    if stylist and "services" in stylist and stylist["services"]:
        current = stylist["services"][0]

    merged = {**(current or {}), **service_data, "id": service_id}
    # Normalize type
    t = str(merged.get("type", current.get("type") if current else "online")).lower()
    merged["type"] = "inperson" if t == "inperson" else "online"

    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id), "services.id": service_id},
        {"$set": {"services.$": merged}}
    )
    # Recompute min price
    if result.modified_count > 0:
        try:
            stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)}, {"services": 1})
            prices = [float(s.get("price", 0)) for s in (stylist.get("services", []) if stylist else []) if s and s.get("isActive", True) and s.get("price") is not None]
            min_price = float(min(prices)) if prices else 0.0
            await db.db.stylists.update_one({"_id": ObjectId(stylist_id)}, {"$set": {"price": min_price}})
        except Exception:
            pass
    return result.modified_count > 0

async def remove_service(stylist_id: str, service_id: str) -> bool:
    """
    Remove a service from stylist's offerings
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$pull": {"services": {"id": service_id}}}
    )
    # Recompute min price
    if result.modified_count > 0:
        try:
            stylist = await db.db.stylists.find_one({"_id": ObjectId(stylist_id)}, {"services": 1})
            prices = [float(s.get("price", 0)) for s in (stylist.get("services", []) if stylist else []) if s and s.get("isActive", True) and s.get("price") is not None]
            min_price = float(min(prices)) if prices else 0.0
            await db.db.stylists.update_one({"_id": ObjectId(stylist_id)}, {"$set": {"price": min_price}})
        except Exception:
            pass
    return result.modified_count > 0

async def get_availability(stylist_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a stylist's availability schedule
    """
    stylist = await get_stylist_by_id(stylist_id)
    if not stylist:
        return None
    return stylist.get("availabilitySchedule", {})

async def update_availability(stylist_id: str, availability_data: Dict[str, Any]) -> bool:
    """
    Update a stylist's availability schedule
    """
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$set": {"availabilitySchedule": availability_data}}
    )
    return result.modified_count > 0

async def update_day_availability(stylist_id: str, day: str, slots: List[Dict[str, str]]) -> bool:
    """
    Update availability for a specific day
    """
    # Validate day input
    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day.lower() not in valid_days:
        return False
        
    # Update the day's slots
    result = await db.db.stylists.update_one(
        {"_id": ObjectId(stylist_id)},
        {"$set": {f"availabilitySchedule.{day.lower()}.slots": slots}}
    )
    return result.modified_count > 0

async def get_available_dates(stylist_id: str, year: int, month: int) -> List[int]:
    """
    Get available dates for a specific month and year
    Returns a list of days where the stylist has availability slots set
    """
    from calendar import monthrange
    import datetime
    
    # Get stylist availability schedule
    availability = await get_availability(stylist_id)
    if not availability:
        return []
        
    # Get the number of days in the month
    _, num_days = monthrange(year, month)
    
    # Determine available dates
    available_dates = []
    for day in range(1, num_days + 1):
        # Create date object to get day of week
        date = datetime.date(year, month, day)
        day_name = date.strftime('%A').lower()
        
        # Check if there are slots for this day in the availability schedule
        if day_name in availability and availability[day_name].get("slots", []):
            available_dates.append(day)
            
    return available_dates
