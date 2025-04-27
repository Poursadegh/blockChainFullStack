from fastapi import APIRouter, WebSocket, Depends, HTTPException
from typing import List
from ...models.social import ChatRoom, ChatParticipant, ChatMessage
from ...services.websocket import chat_service
from ...core.auth import get_current_user
from ...models.user import User

router = APIRouter()

@router.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, current_user: User = Depends(get_current_user)):
    # Verify user is a participant in the room
    participant = await ChatParticipant.filter(
        room_id=room_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant in this chat room")
    
    await chat_service.handle_chat_message(websocket, current_user.id, room_id)

@router.get("/rooms", response_model=List[dict])
async def get_chat_rooms(current_user: User = Depends(get_current_user)):
    rooms = await ChatRoom.filter(
        participants__user_id=current_user.id
    ).prefetch_related("participants")
    
    return [
        {
            "id": room.id,
            "name": room.name,
            "is_group": room.is_group,
            "participants": [
                {
                    "id": p.user_id,
                    "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None
                }
                for p in room.participants
            ]
        }
        for room in rooms
    ]

@router.get("/rooms/{room_id}/messages", response_model=List[dict])
async def get_chat_messages(room_id: int, limit: int = 50, current_user: User = Depends(get_current_user)):
    # Verify user is a participant
    participant = await ChatParticipant.filter(
        room_id=room_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant in this chat room")
    
    messages = await chat_service.get_chat_history(room_id, limit)
    return messages

@router.post("/rooms/{room_id}/read")
async def mark_messages_as_read(room_id: int, current_user: User = Depends(get_current_user)):
    # Verify user is a participant
    participant = await ChatParticipant.filter(
        room_id=room_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant in this chat room")
    
    await chat_service.mark_messages_as_read(room_id, current_user.id)
    return {"status": "success"}

@router.get("/rooms/{room_id}/unread", response_model=dict)
async def get_unread_count(room_id: int, current_user: User = Depends(get_current_user)):
    # Verify user is a participant
    participant = await ChatParticipant.filter(
        room_id=room_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant in this chat room")
    
    count = await chat_service.get_unread_count(room_id, current_user.id)
    return {"unread_count": count}

@router.post("/rooms", response_model=dict)
async def create_chat_room(
    name: str,
    is_group: bool = False,
    participant_ids: List[int] = None,
    current_user: User = Depends(get_current_user)
):
    if not is_group and participant_ids and len(participant_ids) != 1:
        raise HTTPException(status_code=400, detail="Direct chat must have exactly one participant")
    
    # Create the chat room
    room = await ChatRoom.create(
        name=name,
        is_group=is_group
    )
    
    # Add participants
    participants = [current_user.id]
    if participant_ids:
        participants.extend(participant_ids)
    
    for user_id in participants:
        await ChatParticipant.create(
            room_id=room.id,
            user_id=user_id
        )
    
    return {
        "id": room.id,
        "name": room.name,
        "is_group": room.is_group,
        "participants": participants
    } 