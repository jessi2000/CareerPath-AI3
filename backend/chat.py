from fastapi import APIRouter, HTTPException, Depends
from fastapi_socketio import SocketManager
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from auth import get_current_user
from database import db

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Models
class Message(BaseModel):
    id: Optional[str] = None
    sender_id: str
    recipient_id: str
    content: str
    timestamp: Optional[datetime] = None
    message_type: str = "private"
    read: bool = False

class ChatConversation(BaseModel):
    participant_id: str
    participant_name: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0

# REST API routes for chat
@router.get("/conversations")
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get all conversations for the current user"""
    # Get all messages where user is sender or recipient
    messages = await db.messages.find({
        "$or": [
            {"sender_id": current_user["id"]},
            {"recipient_id": current_user["id"]}
        ]
    }).sort("timestamp", -1).to_list(length=1000)
    
    # Group by conversation partner
    conversations = {}
    for message in messages:
        partner_id = message["recipient_id"] if message["sender_id"] == current_user["id"] else message["sender_id"]
        
        if partner_id not in conversations:
            # Get partner info
            partner = await db.users.find_one({"id": partner_id})
            if partner:
                conversations[partner_id] = {
                    "participant_id": partner_id,
                    "participant_name": partner["full_name"],
                    "last_message": message["content"],
                    "last_message_time": message["timestamp"],
                    "unread_count": 0
                }
        
        # Count unread messages
        if message["recipient_id"] == current_user["id"] and not message["read"]:
            conversations[partner_id]["unread_count"] += 1
    
    return list(conversations.values())

@router.get("/conversation/{partner_id}")
async def get_conversation_messages(
    partner_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get messages in a conversation with a specific user"""
    messages = await db.messages.find({
        "$or": [
            {"sender_id": current_user["id"], "recipient_id": partner_id},
            {"sender_id": partner_id, "recipient_id": current_user["id"]}
        ]
    }).sort("timestamp", 1).to_list(length=None)
    
    # Mark messages as read
    await db.messages.update_many(
        {
            "sender_id": partner_id,
            "recipient_id": current_user["id"],
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    return messages

@router.post("/send-message")
async def send_message(
    message: Message,
    current_user: dict = Depends(get_current_user)
):
    """Send a message via REST API (fallback for when WebSocket is not available)"""
    message_doc = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "recipient_id": message.recipient_id,
        "content": message.content,
        "timestamp": datetime.utcnow(),
        "message_type": "private",
        "read": False
    }
    
    await db.messages.insert_one(message_doc)
    return message_doc

@router.post("/mark-read/{partner_id}")
async def mark_messages_read(
    partner_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark all messages from a partner as read"""
    result = await db.messages.update_many(
        {
            "sender_id": partner_id,
            "recipient_id": current_user["id"],
            "read": False
        },
        {"$set": {"read": True}}
    )
    
    return {"messages_marked_read": result.modified_count}
