from typing import Dict, Any, List, Optional
from app.db.mongodb import db
from app.schemas.chat import ChatRoomCreate, MessageCreate
from app.services.user_service import get_user_by_id
from datetime import datetime
from bson import ObjectId

async def create_chat_room(room_in: ChatRoomCreate, user_id: str) -> Dict[str, Any]:
    """
    Create a new chat room between two users
    """
    # Check if other participant exists
    participant = await get_user_by_id(room_in.participantId)
    if not participant:
        return None
    
    # Check if chat room already exists between these users
    participants = [user_id, room_in.participantId]
    existing_room = await db.db.chatRooms.find_one({
        "participants": {"$all": participants}
    })
    
    if existing_room:
        existing_room["id"] = str(existing_room["_id"])
        return existing_room
    
    # Create new chat room
    room_data = {
        "participants": participants,
        "createdAt": datetime.utcnow(),
        "unreadCounts": {user_id: 0, room_in.participantId: 0}
    }
    
    if room_in.bookingId:
        room_data["bookingId"] = room_in.bookingId
    
    # Insert chat room into database
    result = await db.db.chatRooms.insert_one(room_data)
    
    # Get the created chat room
    created_room = await db.db.chatRooms.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_room["id"] = str(created_room["_id"])
    
    return created_room

async def get_chat_room_by_id(room_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a chat room by ID
    """
    try:
        chat_room = await db.db.chatRooms.find_one({"_id": ObjectId(room_id)})
        if chat_room:
            chat_room["id"] = str(chat_room["_id"])
        return chat_room
    except:
        return None

async def get_user_chat_rooms(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all chat rooms for a user
    """
    cursor = db.db.chatRooms.find({
        "participants": user_id
    }).sort("lastMessageTime", -1)
    
    chat_rooms = await cursor.to_list(length=100)
    
    # Transform _id field to string and add unread count for current user
    for room in chat_rooms:
        room["id"] = str(room["_id"])
        room["unreadCount"] = room.get("unreadCounts", {}).get(user_id, 0)
    
    return chat_rooms

async def create_message(message_in: MessageCreate, sender_id: str) -> Dict[str, Any]:
    """
    Create a new message in a chat room
    """
    # Check if chat room exists
    chat_room = await get_chat_room_by_id(message_in.chatRoomId)
    if not chat_room:
        return None
    
    # Check if sender is a participant
    if sender_id not in chat_room["participants"]:
        return None
    
    # Create message data
    message_data = message_in.dict()
    message_data["senderId"] = sender_id
    message_data["timestamp"] = datetime.utcnow()
    message_data["read"] = False
    
    # Insert message into database
    result = await db.db.chatMessages.insert_one(message_data)
    
    # Get the created message
    created_message = await db.db.chatMessages.find_one({"_id": result.inserted_id})
    
    # Transform the _id field to string
    created_message["id"] = str(created_message["_id"])
    
    # Update chat room with last message
    other_participants = [p for p in chat_room["participants"] if p != sender_id]
    
    update_data = {
        "lastMessage": message_data["message"][:50] + "..." if len(message_data["message"]) > 50 else message_data["message"],
        "lastMessageTime": message_data["timestamp"],
    }
    
    # Increment unread count for other participants
    for participant in other_participants:
        unread_field = f"unreadCounts.{participant}"
        await db.db.chatRooms.update_one(
            {"_id": ObjectId(message_in.chatRoomId)},
            {"$inc": {unread_field: 1}}
        )
    
    # Update chat room
    await db.db.chatRooms.update_one(
        {"_id": ObjectId(message_in.chatRoomId)},
        {"$set": update_data}
    )
    
    return created_message

async def get_chat_messages(room_id: str, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get messages from a chat room with pagination
    """
    cursor = db.db.chatMessages.find({
        "chatRoomId": room_id
    }).sort("timestamp", -1).skip(skip).limit(limit)
    
    messages = await cursor.to_list(length=limit)
    
    # Transform _id field to string
    for message in messages:
        message["id"] = str(message["_id"])
    
    # Reverse to get oldest first
    return messages[::-1]

async def mark_messages_as_read(room_id: str, user_id: str) -> bool:
    """
    Mark all messages in a room as read for a user
    """
    # Update chat room to reset unread count for user
    unread_field = f"unreadCounts.{user_id}"
    await db.db.chatRooms.update_one(
        {"_id": ObjectId(room_id)},
        {"$set": {unread_field: 0}}
    )
    
    # Mark messages as read
    result = await db.db.chatMessages.update_many(
        {"chatRoomId": room_id, "senderId": {"$ne": user_id}, "read": False},
        {"$set": {"read": True}}
    )
    
    return result.modified_count > 0

async def get_chat_room_for_booking(booking_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a chat room associated with a booking
    """
    chat_room = await db.db.chatRooms.find_one({"bookingId": booking_id})
    if chat_room:
        chat_room["id"] = str(chat_room["_id"])
    return chat_room

async def get_chat_room_between_users(user_id1: str, user_id2: str) -> Optional[Dict[str, Any]]:
    """
    Get a chat room between two users
    """
    chat_room = await db.db.chatRooms.find_one({
        "participants": {"$all": [user_id1, user_id2]}
    })
    
    if chat_room:
        chat_room["id"] = str(chat_room["_id"])
    
    return chat_room
