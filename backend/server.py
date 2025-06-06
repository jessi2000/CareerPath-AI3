from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="CareerPath AI API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    education_level: str
    work_experience: str
    current_role: Optional[str] = None
    target_role: str
    industry: str
    skills: List[str] = []
    timeline_months: int
    availability_hours_per_week: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_points: int = 0

class AssessmentData(BaseModel):
    education_level: str
    work_experience: str
    current_role: Optional[str] = None
    target_role: str
    industry: str
    skills: List[str]
    timeline_months: int
    availability_hours_per_week: int

class Milestone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    estimated_hours: int
    resources: List[Dict[str, str]] = []
    status: str = "not_started"  # not_started, in_progress, completed
    order: int

class CareerRoadmap(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    description: str
    milestones: List[Milestone]
    total_estimated_hours: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    progress_percentage: float = 0.0

class ProgressUpdate(BaseModel):
    milestone_id: str
    status: str  # in_progress, completed

class LeaderboardEntry(BaseModel):
    user_name: str
    total_points: int
    milestones_completed: int
    rank: int

# AI Service for Roadmap Generation
class AIRoadmapService:
    def __init__(self):
        self.api_key = os.environ.get('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
    
    async def generate_roadmap(self, assessment: AssessmentData, user_name: str) -> CareerRoadmap:
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"roadmap_{uuid.uuid4()}",
                system_message="""You are an expert career counselor and learning path designer. 
                Generate detailed, actionable career roadmaps with specific milestones, resource recommendations, and realistic timelines.
                
                IMPORTANT: Respond ONLY with valid JSON in the exact format specified. Do not include any explanatory text before or after the JSON.
                
                For each milestone, provide:
                1. Clear, actionable title
                2. Detailed description of what to accomplish
                3. Realistic time estimate in hours
                4. 3-5 specific resources (courses, books, projects, certifications)
                5. Logical progression order
                
                Consider the user's current level, target role, timeline, and available hours per week."""
            ).with_model("anthropic", "claude-3-5-sonnet-20241022").with_max_tokens(4096)
            
            # Generate prompt
            prompt = f"""
            Create a career roadmap for {user_name} with the following details:
            - Current Education: {assessment.education_level}
            - Work Experience: {assessment.work_experience}
            - Current Role: {assessment.current_role or 'Not specified'}
            - Target Role: {assessment.target_role}
            - Industry: {assessment.industry}
            - Current Skills: {', '.join(assessment.skills)}
            - Timeline: {assessment.timeline_months} months
            - Available Hours/Week: {assessment.availability_hours_per_week}
            
            Generate 8-12 milestones that will help them achieve their career goal.
            Each milestone should be 10-40 hours of effort.
            
            Respond with JSON in this exact format:
            {{
                "title": "Career Path: [Current Role] to [Target Role]",
                "description": "A comprehensive roadmap to transition from [current] to [target] in [timeline] months",
                "milestones": [
                    {{
                        "title": "Milestone Title",
                        "description": "Detailed description of what to accomplish",
                        "estimated_hours": 25,
                        "resources": [
                            {{"title": "Resource Name", "url": "https://example.com", "type": "course"}},
                            {{"title": "Book Title", "url": "https://amazon.com/book", "type": "book"}},
                            {{"title": "Project Idea", "url": "", "type": "project"}}
                        ],
                        "order": 1
                    }}
                ],
                "total_estimated_hours": 200
            }}
            """
            
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse the AI response
            import json
            roadmap_data = json.loads(response.strip())
            
            # Create milestones with proper IDs
            milestones = []
            for i, milestone_data in enumerate(roadmap_data["milestones"]):
                milestone = Milestone(
                    title=milestone_data["title"],
                    description=milestone_data["description"],
                    estimated_hours=milestone_data["estimated_hours"],
                    resources=milestone_data["resources"],
                    order=i + 1
                )
                milestones.append(milestone)
            
            # Create roadmap
            roadmap = CareerRoadmap(
                user_id="",  # Will be set when saving
                title=roadmap_data["title"],
                description=roadmap_data["description"],
                milestones=milestones,
                total_estimated_hours=roadmap_data["total_estimated_hours"]
            )
            
            return roadmap
            
        except Exception as e:
            logging.error(f"Error generating roadmap: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate roadmap: {str(e)}")

# Initialize AI service
ai_service = AIRoadmapService()

# Routes
@api_router.get("/")
async def root():
    return {"message": "CareerPath AI API is running"}

@api_router.post("/users", response_model=UserProfile)
async def create_user(profile: UserProfile):
    try:
        user_dict = profile.dict()
        await db.users.insert_one(user_dict)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str):
    try:
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfile(**user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate-roadmap")
async def generate_roadmap(assessment: AssessmentData, user_name: str = "User"):
    try:
        roadmap = await ai_service.generate_roadmap(assessment, user_name)
        return roadmap
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/roadmaps", response_model=CareerRoadmap)
async def save_roadmap(roadmap: CareerRoadmap):
    try:
        roadmap_dict = roadmap.dict()
        await db.roadmaps.insert_one(roadmap_dict)
        return roadmap
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/roadmaps/{user_id}", response_model=List[CareerRoadmap])
async def get_user_roadmaps(user_id: str):
    try:
        roadmaps = await db.roadmaps.find({"user_id": user_id}).to_list(1000)
        return [CareerRoadmap(**roadmap) for roadmap in roadmaps]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/roadmaps/{roadmap_id}/progress")
async def update_milestone_progress(roadmap_id: str, progress: ProgressUpdate):
    try:
        # Get the roadmap
        roadmap = await db.roadmaps.find_one({"id": roadmap_id})
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        
        # Update milestone status
        for milestone in roadmap["milestones"]:
            if milestone["id"] == progress.milestone_id:
                milestone["status"] = progress.status
                break
        
        # Calculate progress percentage
        completed_milestones = sum(1 for m in roadmap["milestones"] if m["status"] == "completed")
        total_milestones = len(roadmap["milestones"])
        progress_percentage = (completed_milestones / total_milestones) * 100
        
        # Update roadmap
        await db.roadmaps.update_one(
            {"id": roadmap_id},
            {"$set": {"milestones": roadmap["milestones"], "progress_percentage": progress_percentage}}
        )
        
        # Award points to user if milestone completed
        if progress.status == "completed":
            await db.users.update_one(
                {"id": roadmap["user_id"]},
                {"$inc": {"total_points": 10}}
            )
        
        return {"success": True, "progress_percentage": progress_percentage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard():
    try:
        users = await db.users.find().sort("total_points", -1).limit(10).to_list(10)
        leaderboard = []
        for i, user in enumerate(users):
            # Count completed milestones for each user
            user_roadmaps = await db.roadmaps.find({"user_id": user["id"]}).to_list(1000)
            completed_milestones = 0
            for roadmap in user_roadmaps:
                completed_milestones += sum(1 for m in roadmap["milestones"] if m["status"] == "completed")
            
            entry = LeaderboardEntry(
                user_name=user["name"],
                total_points=user["total_points"],
                milestones_completed=completed_milestones,
                rank=i + 1
            )
            leaderboard.append(entry)
        
        return leaderboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
