from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from auth import get_current_user, send_reminder_email
from database import db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Models
class Notification(BaseModel):
    id: Optional[str] = None
    user_id: str
    title: str
    message: str
    type: str  # milestone_due, achievement_earned, friend_request, system
    read: bool = False
    created_at: Optional[datetime] = None
    action_url: Optional[str] = None

class NotificationPreferences(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    milestone_reminders: bool = True
    friend_notifications: bool = True
    achievement_notifications: bool = True
    reminder_frequency: str = "weekly"  # daily, weekly, monthly

# Create notification
async def create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    action_url: Optional[str] = None
):
    """Create a new notification for a user"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": datetime.utcnow(),
        "action_url": action_url
    }
    
    await db.notifications.insert_one(notification)
    return notification

# Routes
@router.get("/")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    """Get all notifications for the current user"""
    notifications = await db.notifications.find({
        "user_id": current_user["id"]
    }).sort("created_at", -1).limit(50).to_list(50)
    
    return notifications

@router.get("/unread-count")
async def get_unread_count(current_user: dict = Depends(get_current_user)):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "user_id": current_user["id"],
        "read": False
    })
    
    return {"unread_count": count}

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    result = await db.notifications.update_one(
        {
            "id": notification_id,
            "user_id": current_user["id"]
        },
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}

@router.put("/mark-all-read")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    result = await db.notifications.update_many(
        {"user_id": current_user["id"], "read": False},
        {"$set": {"read": True}}
    )
    
    return {"messages_marked_read": result.modified_count}

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a notification"""
    result = await db.notifications.delete_one({
        "id": notification_id,
        "user_id": current_user["id"]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification deleted"}

# Background tasks for notifications
async def check_milestone_reminders():
    """Background task to check for milestone reminders"""
    # Get all active roadmaps
    roadmaps = await db.roadmaps.find({}).to_list(length=None)
    
    for roadmap in roadmaps:
        user = await db.users.find_one({"id": roadmap["user_id"]})
        if not user or not user.get("settings", {}).get("email_notifications", True):
            continue
        
        # Check for overdue milestones
        for milestone in roadmap["milestones"]:
            if milestone["status"] == "in_progress":
                # Check if milestone has been in progress for more than a week
                # This is a simple check - in production you'd want more sophisticated logic
                
                # Create reminder notification
                await create_notification(
                    user_id=user["id"],
                    title="Milestone Reminder",
                    message=f"Don't forget to work on: {milestone['title']}",
                    notification_type="milestone_due",
                    action_url=f"/roadmap/{roadmap['id']}"
                )
                
                # Send email reminder if enabled
                if user.get("settings", {}).get("email_notifications", True):
                    await send_reminder_email(
                        user["email"],
                        user["full_name"],
                        milestone["title"]
                    )

async def notify_achievement_earned(user_id: str, achievement_title: str):
    """Notify user when they earn an achievement"""
    await create_notification(
        user_id=user_id,
        title="Achievement Unlocked! 🎉",
        message=f"You've earned: {achievement_title}",
        notification_type="achievement_earned",
        action_url="/profile/achievements"
    )

async def notify_friend_request(user_id: str, sender_name: str):
    """Notify user of new friend request"""
    await create_notification(
        user_id=user_id,
        title="New Friend Request",
        message=f"{sender_name} wants to connect with you",
        notification_type="friend_request",
        action_url="/social/friends"
    )

async def notify_friend_accepted(user_id: str, friend_name: str):
    """Notify user when friend request is accepted"""
    await create_notification(
        user_id=user_id,
        title="Friend Request Accepted",
        message=f"{friend_name} is now your friend!",
        notification_type="friend_request",
        action_url="/social/friends"
    )

async def notify_milestone_completed(user_id: str, milestone_title: str, points_earned: int):
    """Notify user when they complete a milestone"""
    await create_notification(
        user_id=user_id,
        title="Milestone Completed! 🎯",
        message=f"Great job! You completed '{milestone_title}' and earned {points_earned} points",
        notification_type="achievement_earned",
        action_url="/dashboard"
    )

# System notification endpoints
@router.post("/system/milestone-completed")
async def system_milestone_completed(
    user_id: str,
    milestone_title: str,
    points_earned: int = 10
):
    """System endpoint to notify milestone completion"""
    await notify_milestone_completed(user_id, milestone_title, points_earned)
    return {"message": "Notification sent"}

@router.post("/system/achievement-earned") 
async def system_achievement_earned(user_id: str, achievement_title: str):
    """System endpoint to notify achievement earned"""
    await notify_achievement_earned(user_id, achievement_title)
    return {"message": "Notification sent"}

@router.post("/system/friend-request")
async def system_friend_request(user_id: str, sender_name: str):
    """System endpoint to notify friend request"""
    await notify_friend_request(user_id, sender_name)
    return {"message": "Notification sent"}
