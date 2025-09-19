from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

async def init_db(client: AsyncIOMotorClient):
    """Initialize database with required indexes"""
    db = client.db
    
    # Create indexes for user_favorites collection
    await db.user_favorites.create_index(
        [("userId", ASCENDING), ("stylistId", ASCENDING)],
        unique=True
    )
    
    # Index for sorting by createdAt
    await db.user_favorites.create_index([("createdAt", DESCENDING)])
    
    # Index for querying by userId
    await db.user_favorites.create_index([("userId", ASCENDING)])
    
    # Index for querying by stylistId
    await db.user_favorites.create_index([("stylistId", ASCENDING)])
    
    print("Database indexes created successfully")
