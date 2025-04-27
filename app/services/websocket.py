from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional
import json
from datetime import datetime
from ..models.social import ChatMessage, ChatRoom, ChatParticipant
from .cache import cache_service

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.room_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        await self.update_online_users()

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        await self.update_online_users()

    async def connect_to_room(self, websocket: WebSocket, room_id: int):
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)

    async def disconnect_from_room(self, websocket: WebSocket, room_id: int):
        if room_id in self.room_connections:
            self.room_connections[room_id].remove(websocket)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]

    async def broadcast_to_room(self, room_id: int, message: dict):
        if room_id in self.room_connections:
            for connection in self.room_connections[room_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    await self.disconnect_from_room(connection, room_id)

    async def send_personal_message(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    await self.disconnect(connection, user_id)

    async def update_online_users(self):
        online_users = list(self.active_connections.keys())
        await cache_service.set_online_users(online_users)

class ChatService:
    def __init__(self):
        self.manager = ConnectionManager()

    async def handle_chat_message(self, websocket: WebSocket, user_id: int, room_id: int):
        await self.manager.connect_to_room(websocket, room_id)
        try:
            while True:
                data = await websocket.receive_json()
                message = await ChatMessage.create(
                    room_id=room_id,
                    sender_id=user_id,
                    content=data["content"]
                )
                
                # Update participant's last read time
                await ChatParticipant.filter(
                    room_id=room_id,
                    user_id=user_id
                ).update(last_read_at=datetime.now())

                # Broadcast message to room
                message_data = {
                    "type": "message",
                    "room_id": room_id,
                    "sender_id": user_id,
                    "content": data["content"],
                    "timestamp": message.created_at.isoformat()
                }
                await self.manager.broadcast_to_room(room_id, message_data)

                # Update cache
                await cache_service.clear_post_cache(room_id)

        except WebSocketDisconnect:
            await self.manager.disconnect_from_room(websocket, room_id)

    async def get_chat_history(self, room_id: int, limit: int = 50):
        # Try to get from cache first
        cached_messages = await cache_service.get_chat_messages(room_id, limit)
        if cached_messages:
            return cached_messages

        # If not in cache, get from database
        messages = await ChatMessage.filter(room_id=room_id).order_by("-created_at").limit(limit)
        message_data = [
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        # Cache the results
        await cache_service.set_chat_messages(room_id, message_data, limit)
        return message_data

    async def mark_messages_as_read(self, room_id: int, user_id: int):
        await ChatMessage.filter(
            room_id=room_id,
            sender_id__not=user_id,
            is_read=False
        ).update(is_read=True)

        # Update participant's last read time
        await ChatParticipant.filter(
            room_id=room_id,
            user_id=user_id
        ).update(last_read_at=datetime.now())

    async def get_unread_count(self, room_id: int, user_id: int) -> int:
        return await ChatMessage.filter(
            room_id=room_id,
            sender_id__not=user_id,
            is_read=False,
            created_at__gt=await ChatParticipant.filter(
                room_id=room_id,
                user_id=user_id
            ).values_list("last_read_at", flat=True).first()
        ).count()

chat_service = ChatService() 