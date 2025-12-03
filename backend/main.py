from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import Optional, List
import os
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Body
import jwt
from passlib.context import CryptContext
from PIL import Image
import io
import base64
from pymongo.errors import DuplicateKeyError, OperationFailure, ServerSelectionTimeoutError

load_dotenv()

app = FastAPI(title="GeoNLI API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL") or "mongodb://geonli_app:geonli_app_pw@localhost:27017/geonli?authSource=geonli"
client = AsyncIOMotorClient(MONGODB_URL)
db = client.geonli

# JWT / Auth Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "geonli")
JWT_ALG = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Pydantic Models
class ChatMessage(BaseModel):
    sessionId: str
    message: str
    imageUrl: Optional[str] = None

class CreateSession(BaseModel):
    imageUrl: str
    initialPrompt: str

class Overlay(BaseModel):
    id: str
    type: str  # "box" or "pin"
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    label: Optional[str] = None
    color: Optional[str] = None

class SignupPayload(BaseModel):
    email: str
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

# Authentication Dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Optional Authentication Dependency for guest sessions
async def get_current_user_optional(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    # Prefer Firebase auth if provided
    if not credentials:
        # Fallback to guest header
        guest_id = request.headers.get('X-Guest-Id')
        if guest_id:
            return f"guest:{guest_id}"
        return None  # Guest user without id
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except Exception:
        # Invalid token, try guest header
        guest_id = request.headers.get('X-Guest-Id')
        if guest_id:
            return f"guest:{guest_id}"
        return None  # treat as anonymous guest

# Mock AI Response Generator
def generate_mock_ai_response(prompt: str) -> str:
    responses = [
        f"I've analyzed the image based on your query: '{prompt}'. The satellite imagery shows interesting geographical features.",
        f"Based on '{prompt}', I can identify several key elements in this image.",
        f"Analyzing your question '{prompt}' - the image reveals distinctive patterns and structures.",
    ]
    import random
    return random.choice(responses)

def generate_mock_overlays() -> List[dict]:
    import random
    overlays = []
    
    # Random boxes
    for i in range(random.randint(1, 3)):
        overlays.append({
            "id": f"box-{uuid.uuid4().hex[:8]}",
            "type": "box",
            "x": random.randint(50, 500),
            "y": random.randint(50, 400),
            "width": random.randint(100, 250),
            "height": random.randint(80, 200),
            "label": random.choice(["Building", "Road", "Vegetation", "Water Body", "Structure"]),
            "color": random.choice(["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"])
        })
    
    # Random pins
    for i in range(random.randint(1, 2)):
        overlays.append({
            "id": f"pin-{uuid.uuid4().hex[:8]}",
            "type": "pin",
            "x": random.randint(100, 600),
            "y": random.randint(100, 500),
            "label": random.choice(["POI", "Location", "Marker", "Point of Interest"]),
            "color": random.choice(["#ff8800", "#00ffff", "#8800ff"])
        })
    
    return overlays

def create_thumbnail(image_data: bytes, max_size: tuple = (150, 150)) -> str:
    """Create a downscaled thumbnail from image data"""
    img = Image.open(io.BytesIO(image_data))
    
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # Create thumbnail (maintains aspect ratio)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Save to bytes
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=70, optimize=True)
    buffer.seek(0)
    
    # Convert to base64
    thumbnail_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{thumbnail_base64}"

def create_access_token(subject: str, expires_minutes: int = 60 * 24 * 30) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now.timestamp()) + expires_minutes * 60),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email})

@app.post("/api/auth/signup")
async def signup(data: SignupPayload):
    try:
        existing = await get_user_by_email(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        hashed = pwd_context.hash(data.password)
        user_id = str(uuid.uuid4())
        await db.users.insert_one({
            "_id": user_id,
            "email": data.email,
            "password_hash": hashed,
            "createdAt": datetime.now(timezone.utc).isoformat()
        })
        token = create_access_token(user_id)
        return {"token": token, "user": {"uid": user_id, "email": data.email}}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email already registered")
    except OperationFailure as e:
        # Surface auth vs generic DB errors more clearly
        if getattr(e, 'code', None) == 18 or getattr(e, 'codeName', '') == 'AuthenticationFailed':
            raise HTTPException(status_code=500, detail="Database authentication failed. Check Mongo credentials (MONGODB_URL).")
        raise HTTPException(status_code=500, detail="Database operation failed.")
    except ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="Database unavailable. Please try again later.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/login")
async def login(data: LoginPayload):
    user = await get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not pwd_context.verify(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user["_id"])
    return {"token": token, "user": {"uid": user["_id"], "email": user["email"]}}

# API Endpoints

@app.get("/")
async def root():
    return {"message": "GeoNLI API is running", "version": "1.0.0"}

@app.post("/api/upload")
async def upload_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        image_data = await image.read()
        
        image_base64 = f"data:{image.content_type};base64,{base64.b64encode(image_data).decode()}"
        
        # Create downscaled thumbnail for session list
        thumbnail = create_thumbnail(image_data)
        
        # Generate mock AI response and overlays
        initial_response = generate_mock_ai_response(prompt) if prompt else "Image uploaded successfully!"
        overlays = generate_mock_overlays()
        
        messages_to_insert = []
        if prompt:
            messages_to_insert = [
                {
                    "messageId": str(uuid.uuid4()),
                    "sessionId": session_id,
                    "from": "user",
                    "text": prompt,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "messageId": str(uuid.uuid4()),
                    "sessionId": session_id,
                    "from": "ai",
                    "text": initial_response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
            if messages_to_insert:
                await db.messages.insert_many(messages_to_insert)
        
        image_doc = {
            "sessionId": session_id,
            "imageUrl": image_base64,
            "overlays": overlays,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.images.insert_one(image_doc)
        
        # Create session for authenticated users or guests with id
        if user_id:
            session_doc = {
                "sessionId": session_id,
                "userId": user_id,
                "thumbnail": thumbnail,
                "initialPrompt": prompt or "",
                "messageCount": len(messages_to_insert),
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "updatedAt": datetime.now(timezone.utc).isoformat()
            }
            await db.sessions.insert_one(session_doc)
        
        return {
            "sessionId": session_id,
            "imageUrl": image_base64,
            "thumbnail": thumbnail,
            "initialResponse": initial_response if prompt else None,
            "overlays": overlays
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def send_message(
    chat_message: ChatMessage,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        # For guest users, skip session verification
        session = None
        if user_id:
            session = await db.sessions.find_one({
                "sessionId": chat_message.sessionId,
                "userId": user_id
            })
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        
        ai_response = generate_mock_ai_response(chat_message.message)
        import random
        new_overlays = generate_mock_overlays() if random.random() > 0.5 else []
        # Add messages to messages collection
        messages_to_insert = [
            {
                "messageId": str(uuid.uuid4()),
                "sessionId": chat_message.sessionId,
                "from": "user",
                "text": chat_message.message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "messageId": str(uuid.uuid4()),
                "sessionId": chat_message.sessionId,
                "from": "ai",
                "text": ai_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        await db.messages.insert_many(messages_to_insert)
        
        if new_overlays:
            await db.images.update_one(
                {"sessionId": chat_message.sessionId},
                {"$set": {"overlays": new_overlays}}
            )
        
        # Update session only if user is authenticated
        if user_id and session:
            await db.sessions.update_one(
                {"sessionId": chat_message.sessionId},
                {
                    "$set": {"updatedAt": datetime.now(timezone.utc).isoformat()},
                    "$inc": {"messageCount": 2}
                }
            )
        
        return {
            "message": ai_response,
            "overlays": new_overlays if new_overlays else (session.get("overlays", []) if session else [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{session_id}")
async def get_chat_history(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        # For authenticated users, verify session ownership
        if user_id:
            session = await db.sessions.find_one({
                "sessionId": session_id,
                "userId": user_id
            })
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        
        messages = await db.messages.find(
            {"sessionId": session_id},
            {"_id": 0, "messageId": 1, "from": 1, "text": 1, "timestamp": 1}
        ).sort("timestamp", 1).to_list(1000)
        
        # Convert messageId to id for frontend compatibility
        for msg in messages:
            msg["id"] = msg.pop("messageId")
        
        return {
            "messages": messages
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions(user_id: Optional[str] = Depends(get_current_user_optional)):
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated or guest id missing")
        sessions = await db.sessions.find(
            {"userId": user_id},
            {"_id": 0, "sessionId": 1, "thumbnail": 1, "initialPrompt": 1, "createdAt": 1, "updatedAt": 1, "messageCount": 1}
        ).sort("updatedAt", -1).to_list(100)
        
        return {"sessions": sessions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/image")
async def get_session_image(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        # For authenticated users, verify session ownership
        if user_id:
            session = await db.sessions.find_one(
                {"sessionId": session_id, "userId": user_id},
                {"_id": 0, "sessionId": 1}
            )
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        
        # Fetch image from images collection
        image_data = await db.images.find_one(
            {"sessionId": session_id},
            {"_id": 0, "imageUrl": 1, "overlays": 1}
        )
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")
        
        return {
            "imageUrl": image_data.get("imageUrl"),
            "overlays": image_data.get("overlays", [])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
async def create_session(
    session_data: CreateSession,
    user_id: str = Depends(get_current_user)
):
    try:
        session_id = str(uuid.uuid4())
        
        # Generate mock AI response
        initial_response = generate_mock_ai_response(session_data.initialPrompt)
        overlays = generate_mock_overlays()
        
        # Store messages separately
        messages_to_insert = [
            {
                "messageId": str(uuid.uuid4()),
                "sessionId": session_id,
                "from": "user",
                "text": session_data.initialPrompt,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "messageId": str(uuid.uuid4()),
                "sessionId": session_id,
                "from": "ai",
                "text": initial_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        await db.messages.insert_many(messages_to_insert)
        
        # Create thumbnail if imageUrl is base64
        thumbnail = session_data.imageUrl
        if session_data.imageUrl.startswith('data:image'):
            # Extract base64 data
            image_data_bytes = base64.b64decode(session_data.imageUrl.split(',')[1])
            thumbnail = create_thumbnail(image_data_bytes)
        
        image_doc = {
            "sessionId": session_id,
            "imageUrl": session_data.imageUrl,
            "overlays": overlays,
            "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.images.insert_one(image_doc)
        
        session_doc = {
            "sessionId": session_id,
            "userId": user_id,
            "thumbnail": thumbnail,
            "initialPrompt": session_data.initialPrompt,
            "messageCount": 2,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        
        await db.sessions.insert_one(session_doc)
        
        return {
            "sessionId": session_id,
            "imageUrl": session_data.imageUrl,
            "thumbnail": thumbnail,
            "initialResponse": initial_response
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        # Delete session
        result = await db.sessions.delete_one({
            "sessionId": session_id,
            "userId": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
    
        await db.messages.delete_many({"sessionId": session_id})
        await db.images.delete_one({"sessionId": session_id})
        
        return {"success": True, "message": "Session deleted"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
