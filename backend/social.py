from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from backend.auth import get_current_user
from backend.database import db

router = APIRouter(prefix="/api/social", tags=["social"])

# Models
class FriendRequest(BaseModel):
    recipient_email: str
    message: Optional[str] = ""

class FriendResponse(BaseModel):
    request_id: str
    accept: bool

class Achievement(BaseModel):
    id: str
    title: str
    description: str
    icon: str
    points: int
    date_earned: datetime

class Badge(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    rarity: str  # common, rare, epic, legendary
    date_earned: datetime

# Friend system routes
@router.post("/friend-request")
async def send_friend_request(
    request: FriendRequest,
    current_user: dict = Depends(get_current_user)
):
    # Find recipient
    recipient = await db.users.find_one({"email": request.recipient_email})
    if not recipient:
        raise HTTPException(status_code=404, detail="User not found")
    
    if recipient["email"] == current_user["email"]:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check if already friends or request exists
    existing_request = await db.friend_requests.find_one({
        "$or": [
            {"sender_id": current_user["id"], "recipient_id": recipient["id"]},
            {"sender_id": recipient["id"], "recipient_id": current_user["id"]}
        ],
        "status": {"$in": ["pending", "accepted"]}
    })
    
    if existing_request:
        if existing_request["status"] == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        else:
            raise HTTPException(status_code=400, detail="Friend request already sent")
    
    # Create friend request
    friend_request = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "recipient_id": recipient["id"],
        "sender_name": current_user["full_name"],
        "recipient_name": recipient["full_name"],
        "message": request.message,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    await db.friend_requests.insert_one(friend_request)
    return {"message": "Friend request sent successfully"}

@router.get("/friend-requests")
async def get_friend_requests(current_user: dict = Depends(get_current_user)):
    # Get pending requests sent to current user
    requests = await db.friend_requests.find({
        "recipient_id": current_user["id"],
        "status": "pending"
    }).to_list(length=None)
    
    return requests

@router.post("/friend-request/respond")
async def respond_to_friend_request(
    response: FriendResponse,
    current_user: dict = Depends(get_current_user)
):
    # Find the request
    request = await db.friend_requests.find_one({
        "id": response.request_id,
        "recipient_id": current_user["id"],
        "status": "pending"
    })
    
    if not request:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    status = "accepted" if response.accept else "rejected"
    
    # Update request status
    await db.friend_requests.update_one(
        {"id": response.request_id},
        {"$set": {"status": status, "responded_at": datetime.utcnow()}}
    )
    
    if response.accept:
        # Add to friends lists
        await db.friendships.insert_one({
            "id": str(uuid.uuid4()),
            "user1_id": request["sender_id"],
            "user2_id": current_user["id"],
            "created_at": datetime.utcnow()
        })
        
        # Update friend counts
        await db.users.update_one(
            {"id": request["sender_id"]},
            {"$inc": {"achievements.friends_connected": 1}}
        )
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$inc": {"achievements.friends_connected": 1}}
        )
    
    return {"message": f"Friend request {status}"}

@router.get("/friends")
async def get_friends(current_user: dict = Depends(get_current_user)):
    # Get friendships
    friendships = await db.friendships.find({
        "$or": [
            {"user1_id": current_user["id"]},
            {"user2_id": current_user["id"]}
        ]
    }).to_list(length=None)
    
    # Get friend user IDs
    friend_ids = []
    for friendship in friendships:
        if friendship["user1_id"] == current_user["id"]:
            friend_ids.append(friendship["user2_id"])
        else:
            friend_ids.append(friendship["user1_id"])
    
    # Get friend details
    friends = await db.users.find({
        "id": {"$in": friend_ids}
    }).to_list(length=None)
    
    # Remove sensitive data
    friend_list = []
    for friend in friends:
        friend_info = {
            "id": friend["id"],
            "full_name": friend["full_name"],
            "email": friend["email"],
            "level": friend.get("level", 1),
            "total_points": friend.get("total_points", 0),
            "profile": friend.get("profile", {}),
            "last_login": friend.get("last_login"),
            "achievements": friend.get("achievements", {})
        }
        friend_list.append(friend_info)
    
    return friend_list

# Achievements and badges
@router.get("/achievements")
async def get_achievements(current_user: dict = Depends(get_current_user)):
    achievements = current_user.get("achievements", {})
    badges = current_user.get("badges", [])
    
    # Calculate potential new achievements
    milestones_completed = achievements.get("milestones_completed", 0)
    points_earned = achievements.get("points_earned", 0)
    friends_connected = achievements.get("friends_connected", 0)
    
    available_badges = []
    
    # Achievement logic
    if milestones_completed >= 1 and not any(b.get("id") == "first_milestone" for b in badges):
        available_badges.append({
            "id": "first_milestone",
            "name": "First Step",
            "description": "Complete your first milestone",
            "icon": "🎯",
            "rarity": "common"
        })
    
    if milestones_completed >= 5 and not any(b.get("id") == "milestone_master" for b in badges):
        available_badges.append({
            "id": "milestone_master", 
            "name": "Milestone Master",
            "description": "Complete 5 milestones",
            "icon": "🏆",
            "rarity": "rare"
        })
    
    if points_earned >= 100 and not any(b.get("id") == "point_collector" for b in badges):
        available_badges.append({
            "id": "point_collector",
            "name": "Point Collector", 
            "description": "Earn 100 points",
            "icon": "💎",
            "rarity": "rare"
        })
    
    if friends_connected >= 3 and not any(b.get("id") == "social_butterfly" for b in badges):
        available_badges.append({
            "id": "social_butterfly",
            "name": "Social Butterfly",
            "description": "Connect with 3 friends",
            "icon": "🦋",
            "rarity": "epic"
        })
    
    return {
        "current_achievements": achievements,
        "earned_badges": badges,
        "available_badges": available_badges
    }

@router.post("/claim-badge/{badge_id}")
async def claim_badge(badge_id: str, current_user: dict = Depends(get_current_user)):
    # Get available badges
    achievements_data = await get_achievements(current_user)
    available_badges = achievements_data["available_badges"]
    
    # Find the badge
    badge_to_claim = None
    for badge in available_badges:
        if badge["id"] == badge_id:
            badge_to_claim = badge
            break
    
    if not badge_to_claim:
        raise HTTPException(status_code=404, detail="Badge not available")
    
    # Add badge to user
    badge_with_date = {
        **badge_to_claim,
        "date_earned": datetime.utcnow()
    }
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$push": {"badges": badge_with_date}}
    )
    
    # Award points for badge
    badge_points = {"common": 10, "rare": 25, "epic": 50, "legendary": 100}
    points = badge_points.get(badge_to_claim["rarity"], 10)
    
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"total_points": points, "achievements.points_earned": points}}
    )
    
    return {"message": f"Badge '{badge_to_claim['name']}' claimed! +{points} points"}

@router.get("/leaderboard/extended")
async def get_extended_leaderboard():
    # Get top users by points
    users = await db.users.find().sort("total_points", -1).limit(20).to_list(20)
    
    leaderboard = []
    for i, user in enumerate(users):
        # Count completed milestones
        user_roadmaps = await db.roadmaps.find({"user_id": user["id"]}).to_list(1000)
        completed_milestones = 0
        for roadmap in user_roadmaps:
            completed_milestones += sum(1 for m in roadmap["milestones"] if m["status"] == "completed")
        
        entry = {
            "rank": i + 1,
            "user_name": user["full_name"],
            "total_points": user.get("total_points", 0),
            "level": user.get("level", 1),
            "milestones_completed": completed_milestones,
            "badges_count": len(user.get("badges", [])),
            "friends_count": user.get("achievements", {}).get("friends_connected", 0),
            "profile": user.get("profile", {})
        }
        leaderboard.append(entry)
    
    return leaderboard

@router.get("/discover-users")
async def discover_users(current_user: dict = Depends(get_current_user)):
    # Get users with similar interests/goals
    current_profile = current_user.get("profile", {})
    target_role = current_profile.get("target_role", "")
    industry = current_profile.get("industry", "")
    
    # Get current friend IDs
    friendships = await db.friendships.find({
        "$or": [
            {"user1_id": current_user["id"]},
            {"user2_id": current_user["id"]}
        ]
    }).to_list(length=None)
    
    friend_ids = [current_user["id"]]  # Include self to exclude
    for friendship in friendships:
        if friendship["user1_id"] == current_user["id"]:
            friend_ids.append(friendship["user2_id"])
        else:
            friend_ids.append(friendship["user1_id"])
    
    # Find similar users
    similar_users = await db.users.find({
        "id": {"$nin": friend_ids},
        "$or": [
            {"profile.target_role": {"$regex": target_role, "$options": "i"}},
            {"profile.industry": industry}
        ]
    }).limit(10).to_list(10)
    
    # Format response
    suggestions = []
    for user in similar_users:
        suggestions.append({
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "profile": user.get("profile", {}),
            "total_points": user.get("total_points", 0),
            "level": user.get("level", 1),
            "badges_count": len(user.get("badges", []))
        })
    
    return suggestions
