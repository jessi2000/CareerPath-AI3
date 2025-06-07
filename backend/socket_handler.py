import socketio
from typing import Dict
import uuid
from datetime import datetime
import asyncio

from backend.database import db
from backend.auth import verify_token

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi'
)

# Store active connections
connected_users: Dict[str, str] = {}  # {user_id: socket_id}
user_sessions: Dict[str, str] = {}    # {socket_id: user_id}

@sio.event
async def connect(sid, environ, auth):
    """Handle user connection"""
    try:
        # Extract token from auth
        token = auth.get("token") if auth else None
        if not token:
            await sio.disconnect(sid)
            return False
        
        # Verify token and get user
        email = verify_token(token)
        if not email:
            await sio.disconnect(sid)
            return False
        
        user = await db.users.find_one({"email": email})
        if not user:
            await sio.disconnect(sid)
            return False
        
        user_id = user["id"]
        
        # Store connection
        connected_users[user_id] = sid
        user_sessions[sid] = user_id
        
        # Update user online status
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "online": True,
                    "last_seen": datetime.utcnow(),
                    "socket_id": sid
                }
            }
        )
        
        # Notify friends that user is online
        await notify_friends_status_change(user_id, True)
        
        # Join user to their personal room
        await sio.enter_room(sid, f"user_{user_id}")
        
        print(f"✅ User {user['full_name']} ({user_id}) connected with session {sid}")
        
        # Send recent messages
        await send_recent_messages(sid, user_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        await sio.disconnect(sid)
        return False

@sio.event
async def disconnect(sid):
    """Handle user disconnection"""
    try:
        user_id = user_sessions.get(sid)
        if user_id:
            # Remove from connected users
            connected_users.pop(user_id, None)
            user_sessions.pop(sid, None)
            
            # Update user offline status
            await db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "online": False,
                        "last_seen": datetime.utcnow()
                    },
                    "$unset": {"socket_id": ""}
                }
            )
            
            # Notify friends that user is offline
            await notify_friends_status_change(user_id, False)
            
            print(f"❌ User {user_id} disconnected")
            
    except Exception as e:
        print(f"❌ Disconnection error: {e}")

@sio.event
async def private_message(sid, data):
    """Handle private messages between users"""
    try:
        user_id = user_sessions.get(sid)
        if not user_id:
            await sio.emit("error", {"message": "Not authenticated"}, room=sid)
            return
        
        recipient_id = data.get("recipient_id")
        content = data.get("content")
        
        if not recipient_id or not content:
            await sio.emit("error", {"message": "Missing recipient_id or content"}, room=sid)
            return
        
        # Verify recipient exists
        recipient = await db.users.find_one({"id": recipient_id})
        if not recipient:
            await sio.emit("error", {"message": "Recipient not found"}, room=sid)
            return
        
        # Create message
        message = {
            "id": str(uuid.uuid4()),
            "sender_id": user_id,
            "recipient_id": recipient_id,
            "content": content,
            "timestamp": datetime.utcnow(),
            "message_type": "private",
            "read": False
        }
        
        # Save to database
        await db.messages.insert_one(message)
        
        # Send to recipient if online
        recipient_sid = connected_users.get(recipient_id)
        if recipient_sid:
            await sio.emit("new_message", {
                "id": message["id"],
                "sender_id": user_id,
                "content": content,
                "timestamp": message["timestamp"].isoformat(),
                "read": False
            }, room=recipient_sid)
        
        # Send confirmation to sender
        await sio.emit("message_sent", {
            "message_id": message["id"],
            "timestamp": message["timestamp"].isoformat(),
            "status": "sent"
        }, room=sid)
        
        print(f"📤 Message sent from {user_id} to {recipient_id}")
        
    except Exception as e:
        print(f"❌ Private message error: {e}")
        await sio.emit("error", {"message": "Failed to send message"}, room=sid)

@sio.event
async def typing(sid, data):
    """Handle typing indicators"""
    try:
        user_id = user_sessions.get(sid)
        if not user_id:
            return
        
        recipient_id = data.get("recipient_id")
        is_typing = data.get("is_typing", False)
        
        if recipient_id:
            recipient_sid = connected_users.get(recipient_id)
            if recipient_sid:
                await sio.emit("user_typing", {
                    "user_id": user_id,
                    "is_typing": is_typing
                }, room=recipient_sid)
                
    except Exception as e:
        print(f"❌ Typing indicator error: {e}")

@sio.event
async def mark_read(sid, data):
    """Mark messages as read"""
    try:
        user_id = user_sessions.get(sid)
        if not user_id:
            return
        
        sender_id = data.get("sender_id")
        if not sender_id:
            return
        
        # Mark messages as read
        result = await db.messages.update_many(
            {
                "sender_id": sender_id,
                "recipient_id": user_id,
                "read": False
            },
            {"$set": {"read": True}}
        )
        
        # Notify sender about read receipts
        sender_sid = connected_users.get(sender_id)
        if sender_sid:
            await sio.emit("messages_read", {
                "reader_id": user_id,
                "count": result.modified_count
            }, room=sender_sid)
            
    except Exception as e:
        print(f"❌ Mark read error: {e}")

@sio.event
async def join_room(sid, data):
    """Join a specific room"""
    try:
        room = data.get("room")
        if room:
            await sio.enter_room(sid, room)
            await sio.emit("joined_room", {"room": room}, room=sid)
    except Exception as e:
        print(f"❌ Join room error: {e}")

@sio.event
async def leave_room(sid, data):
    """Leave a specific room"""
    try:
        room = data.get("room")
        if room:
            await sio.leave_room(sid, room)
            await sio.emit("left_room", {"room": room}, room=sid)
    except Exception as e:
        print(f"❌ Leave room error: {e}")

# Helper functions
async def notify_friends_status_change(user_id: str, online: bool):
    """Notify friends when user comes online/offline"""
    try:
        # Get user's friends
        friendships = await db.friendships.find({
            "$or": [
                {"user1_id": user_id},
                {"user2_id": user_id}
            ]
        }).to_list(length=None)
        
        # Get friend IDs
        friend_ids = []
        for friendship in friendships:
            if friendship["user1_id"] == user_id:
                friend_ids.append(friendship["user2_id"])
            else:
                friend_ids.append(friendship["user1_id"])
        
        # Notify online friends
        for friend_id in friend_ids:
            friend_sid = connected_users.get(friend_id)
            if friend_sid:
                await sio.emit("friend_status_change", {
                    "user_id": user_id,
                    "online": online
                }, room=friend_sid)
                
    except Exception as e:
        print(f"❌ Friend status notification error: {e}")

async def send_recent_messages(sid: str, user_id: str):
    """Send recent message history to newly connected user"""
    try:
        # Get recent messages
        messages = await db.messages.find({
            "$or": [
                {"sender_id": user_id},
                {"recipient_id": user_id}
            ]
        }).sort("timestamp", -1).limit(50).to_list(50)
        
        # Format and send
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg["id"],
                "sender_id": msg["sender_id"],
                "recipient_id": msg["recipient_id"],
                "content": msg["content"],
                "timestamp": msg["timestamp"].isoformat(),
                "read": msg["read"]
            })
        
        await sio.emit("message_history", {
            "messages": formatted_messages
        }, room=sid)
        
    except Exception as e:
        print(f"❌ Send message history error: {e}")

async def broadcast_notification(user_id: str, notification: dict):
    """Broadcast notification to user if online"""
    try:
        user_sid = connected_users.get(user_id)
        if user_sid:
            await sio.emit("new_notification", notification, room=user_sid)
    except Exception as e:
        print(f"❌ Broadcast notification error: {e}")

# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)
