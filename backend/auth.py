from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import uuid

from database import db

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserSettings(BaseModel):
    email_notifications: bool = True
    reminder_frequency: str = "weekly"  # daily, weekly, monthly, none
    theme: str = "light"  # light, dark
    
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    current_role: Optional[str] = None
    target_role: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[list] = None

# Security functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

# Mock email service
async def send_welcome_email(email: str, name: str):
    # Mock email - in production, replace with real email service
    print(f"📧 MOCK EMAIL: Welcome email sent to {email} for {name}")
    
async def send_reminder_email(email: str, name: str, milestone_title: str):
    # Mock email - in production, replace with real email service  
    print(f"📧 MOCK EMAIL: Reminder sent to {email} for {name} about '{milestone_title}'")

# Routes
@router.post("/register", response_model=Token)
async def register(user_data: UserRegister, background_tasks: BackgroundTasks):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    user_id = str(uuid.uuid4())
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "total_points": 0,
        "level": 1,
        "badges": [],
        "completed_courses": [],
        "knowledge_areas": [],
        "settings": {
            "email_notifications": True,
            "reminder_frequency": "weekly",
            "theme": "light"
        },
        "profile": {
            "bio": "",
            "current_role": "",
            "target_role": "",
            "skills": [],
            "education_level": "",
            "work_experience": "",
            "industry": "",
            "avatar": "",
            "social_links": []
        },
        "achievements": {
            "first_login": datetime.utcnow(),
            "milestones_completed": 0,
            "courses_completed": 0,
            "points_earned": 0,
            "friends_connected": 0
        }
    }
    
    await db.users.insert_one(user_doc)
    
    # Send welcome email in background
    background_tasks.add_task(send_welcome_email, user_data.email, user_data.full_name)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.email}, expires_delta=access_token_expires
    )
    
    # Remove sensitive data from user object
    user_response = {k: v for k, v in user_doc.items() if k != "hashed_password"}
    
    return Token(access_token=access_token, user=user_response)

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    user = await db.users.find_one({"email": user_credentials.email})
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    await db.users.update_one(
        {"email": user_credentials.email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    # Remove sensitive data
    user_response = {k: v for k, v in user.items() if k != "hashed_password"}
    
    return Token(access_token=access_token, user=user_response)

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    # Remove sensitive data
    user_response = {k: v for k, v in current_user.items() if k != "hashed_password"}
    return user_response

@router.put("/profile")
async def update_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_data = {}
    
    if user_update.full_name:
        update_data["full_name"] = user_update.full_name
    if user_update.current_role:
        update_data["profile.current_role"] = user_update.current_role
    if user_update.target_role:
        update_data["profile.target_role"] = user_update.target_role
    if user_update.bio:
        update_data["profile.bio"] = user_update.bio
    if user_update.skills:
        update_data["profile.skills"] = user_update.skills
    
    if update_data:
        await db.users.update_one(
            {"email": current_user["email"]},
            {"$set": update_data}
        )
    
    # Return updated user
    updated_user = await db.users.find_one({"email": current_user["email"]})
    user_response = {k: v for k, v in updated_user.items() if k != "hashed_password"}
    return user_response

@router.put("/settings")
async def update_settings(
    settings: UserSettings,
    current_user: dict = Depends(get_current_user)
):
    await db.users.update_one(
        {"email": current_user["email"]},
        {"$set": {"settings": settings.dict()}}
    )
    
    updated_user = await db.users.find_one({"email": current_user["email"]})
    user_response = {k: v for k, v in updated_user.items() if k != "hashed_password"}
    return user_response
