from fastapi import APIRouter
from typing import List, Dict, Any
from app.db.mongodb import get_database

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def list_specialities():
    db = await get_database()
    coll = db.get_collection("specialities")
    cursor = coll.find({}).sort([("name", 1)])
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        items.append(doc)
    return items
