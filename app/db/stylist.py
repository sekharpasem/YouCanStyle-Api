from bson import ObjectId
from app.db.mongodb import get_database

# Stylist collection helpers

async def get_stylist_by_id(stylist_id: str):
    """
    Get a stylist document by its ID
    """
    db = await get_database()
    try:
        # Convert string ID to ObjectId
        object_id = ObjectId(stylist_id)
        return await db["stylists"].find_one({"_id": object_id})
    except Exception:
        return None

async def get_stylist_by_user_id(user_id: str):
    """
    Get a stylist document by user ID
    """
    db = await get_database()
    try:
        # Find stylist where userId matches
        return await db["stylists"].find_one({"userId": user_id})
    except Exception:
        return None
