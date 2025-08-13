from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Optional
from app.core.auth import get_current_user
from app.schemas.chat import (
    ChatRoomCreate, MessageCreate, ChatRoomResponse, 
    MessageResponse, ChatRoomWithParticipantsResponse
)
from app.services.chat_service import (
    create_chat_room, get_chat_room_by_id, get_user_chat_rooms,
    create_message, get_chat_messages, mark_messages_as_read,
    get_chat_room_for_booking, get_chat_room_between_users
)
from app.services.user_service import get_user_by_id

router = APIRouter()

@router.post("/rooms", response_model=ChatRoomResponse)
async def create_new_chat_room(
    room_in: ChatRoomCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new chat room or get existing one between current user and another participant
    """
    room = await create_chat_room(room_in, str(current_user["_id"]))
    if not room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create chat room"
        )
    
    # Format response with unread count for current user
    room["unreadCount"] = room.get("unreadCounts", {}).get(str(current_user["_id"]), 0)
    return room

@router.get("/rooms", response_model=List[ChatRoomWithParticipantsResponse])
async def get_my_chat_rooms(current_user: dict = Depends(get_current_user)):
    """
    Get all chat rooms for the current user
    """
    rooms = await get_user_chat_rooms(str(current_user["_id"]))
    
    # Populate participant details
    for room in rooms:
        room["participantDetails"] = []
        for participant_id in room["participants"]:
            if participant_id != str(current_user["_id"]):
                participant = await get_user_by_id(participant_id)
                if participant:
                    participant_info = {
                        "id": participant_id,
                        "fullName": participant.get("fullName", ""),
                        "profileImage": participant.get("profileImage", "")
                    }
                    room["participantDetails"].append(participant_info)
    
    return rooms

@router.get("/rooms/{room_id}", response_model=ChatRoomWithParticipantsResponse)
async def get_chat_room(
    room_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific chat room
    """
    room = await get_chat_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Check if user is a participant
    if str(current_user["_id"]) not in room["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat room"
        )
    
    # Format response with unread count for current user
    room["unreadCount"] = room.get("unreadCounts", {}).get(str(current_user["_id"]), 0)
    
    # Populate participant details
    room["participantDetails"] = []
    for participant_id in room["participants"]:
        if participant_id != str(current_user["_id"]):
            participant = await get_user_by_id(participant_id)
            if participant:
                participant_info = {
                    "id": participant_id,
                    "fullName": participant.get("fullName", ""),
                    "profileImage": participant.get("profileImage", "")
                }
                room["participantDetails"].append(participant_info)
    
    return room

@router.get("/rooms/booking/{booking_id}", response_model=ChatRoomResponse)
async def get_chat_room_by_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a chat room associated with a booking
    """
    room = await get_chat_room_for_booking(booking_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found for this booking"
        )
    
    # Check if user is a participant
    if str(current_user["_id"]) not in room["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat room"
        )
    
    # Format response with unread count for current user
    room["unreadCount"] = room.get("unreadCounts", {}).get(str(current_user["_id"]), 0)
    return room

@router.get("/rooms/user/{user_id}", response_model=ChatRoomResponse)
async def get_chat_room_with_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a chat room between current user and another user
    """
    room = await get_chat_room_between_users(str(current_user["_id"]), user_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found with this user"
        )
    
    # Format response with unread count for current user
    room["unreadCount"] = room.get("unreadCounts", {}).get(str(current_user["_id"]), 0)
    return room

@router.post("/messages", response_model=MessageResponse)
async def send_message(
    message_in: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Send a new message in a chat room
    """
    # Check if chat room exists
    room = await get_chat_room_by_id(message_in.chatRoomId)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Check if user is a participant
    if str(current_user["_id"]) not in room["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat room"
        )
    
    # Create message
    message = await create_message(message_in, str(current_user["_id"]))
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not send message"
        )
    
    return message

@router.get("/messages/{room_id}", response_model=List[MessageResponse])
async def get_room_messages(
    room_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages from a chat room with pagination
    """
    # Check if chat room exists
    room = await get_chat_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Check if user is a participant
    if str(current_user["_id"]) not in room["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat room"
        )
    
    # Get messages
    messages = await get_chat_messages(room_id, skip, limit)
    
    # Mark messages as read
    await mark_messages_as_read(room_id, str(current_user["_id"]))
    
    return messages

@router.put("/rooms/{room_id}/read", response_model=ChatRoomResponse)
async def mark_room_as_read(
    room_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark all messages in a room as read
    """
    # Check if chat room exists
    room = await get_chat_room_by_id(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Check if user is a participant
    if str(current_user["_id"]) not in room["participants"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this chat room"
        )
    
    # Mark messages as read
    await mark_messages_as_read(room_id, str(current_user["_id"]))
    
    # Get updated room
    updated_room = await get_chat_room_by_id(room_id)
    updated_room["unreadCount"] = updated_room.get("unreadCounts", {}).get(str(current_user["_id"]), 0)
    
    return updated_room
