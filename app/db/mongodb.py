from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """Connect to MongoDB."""
    try:
        logger.info("Connecting to MongoDB...")
        db.client = AsyncIOMotorClient(settings.MONGO_URI)
        db.db = db.client[settings.DB_NAME]
        logger.info("Connected to MongoDB.")
        
        # Create indexes for collections
        await create_indexes()
        
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """Close MongoDB connection."""
    if db.client:
        logger.info("Closing MongoDB connection...")
        db.client.close()
        logger.info("MongoDB connection closed.")

async def get_database():
    """Get MongoDB database instance."""
    return db.db

async def create_indexes():
    """Create indexes for collections."""
    try:
        # Users collection indexes
        await db.db.users.create_index("email", unique=True)
        await db.db.users.create_index("phone", unique=True)
        
        # Stylists collection indexes
        await db.db.stylists.create_index("id", unique=True)
        
        # Bookings collection indexes
        await db.db.bookings.create_index("stylistId")
        await db.db.bookings.create_index("clientId")
        await db.db.bookings.create_index([("stylistId", 1), ("date", 1)])
        await db.db.bookings.create_index([("clientId", 1), ("status", 1)])
        
        # Chat rooms collection indexes
        await db.db.chatRooms.create_index("participants")
        
        # Chat messages collection indexes
        await db.db.chatMessages.create_index([("chatRoomId", 1), ("timestamp", 1)])
        
        # Reviews collection indexes
        await db.db.reviews.create_index("stylistId")
        await db.db.reviews.create_index("bookingId", unique=True)
        
        # Users reviews collection indexes (reviews by users about stylists)
        await db.db.users_reviews.create_index("stylistId")
        await db.db.users_reviews.create_index("userId")
        await db.db.users_reviews.create_index("createdAt")
        
        # Stylists reviews collection indexes (reviews by stylists about users)
        await db.db.stylists_reviews.create_index("stylistId")
        await db.db.stylists_reviews.create_index("userId")
        await db.db.stylists_reviews.create_index("createdAt")
        
        # User favorites collection indexes
        await db.db.user_favorites.create_index(
            [("userId", 1), ("stylistId", 1)],
            unique=True
        )
        await db.db.user_favorites.create_index("userId")
        await db.db.user_favorites.create_index("stylistId")
        await db.db.user_favorites.create_index("createdAt")
        
        logger.info("MongoDB indexes created successfully.")
    except Exception as e:
        logger.error(f"Failed to create MongoDB indexes: {e}")
