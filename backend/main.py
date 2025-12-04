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
import tempfile
from gradio_client import Client, handle_file
import requests
import json
import re
import math
from pymongo.errors import DuplicateKeyError, OperationFailure, ServerSelectionTimeoutError

load_dotenv()

# --- GRADIO CLIENT SETUP ---
try:
    # Use 127.0.0.1 to force IPv4
    gradio_app = Client("http://127.0.0.1:7860")
    print("✅ Connected to MGM Container via Gradio Client")
except Exception as e:
    print(f"⚠️ Could not connect to MGM Container: {e}")
    gradio_app = None

app = FastAPI(title="GeoNLI API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://geonli-chat-t99.web.app"],
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

# --- Pydantic Models ---
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
    # Axis-aligned rectangle (legacy)
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    # Oriented quadrilateral (x1,y1 ... x4,y4)
    x1: Optional[float] = None
    y1: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    x3: Optional[float] = None
    y3: Optional[float] = None
    x4: Optional[float] = None
    y4: Optional[float] = None
    label: Optional[str] = None
    color: Optional[str] = None

class SignupPayload(BaseModel):
    email: str
    password: str

class LoginPayload(BaseModel):
    email: str
    password: str

# --- Eval Request Models ---
class InputImageMetadata(BaseModel):
    width: int
    height: int
    spatial_resolution_m: float

class InputImage(BaseModel):
    image_id: str
    image_url: str
    metadata: InputImageMetadata

class CaptionQuery(BaseModel):
    instruction: str

class GroundingQuery(BaseModel):
    instruction: str

class AttributeBinary(BaseModel):
    instruction: str

class AttributeNumeric(BaseModel):
    instruction: str

class AttributeSemantic(BaseModel):
    instruction: str

class AttributeQuery(BaseModel):
    binary: AttributeBinary
    numeric: AttributeNumeric
    semantic: AttributeSemantic

class EvalQueries(BaseModel):
    caption_query: CaptionQuery
    grounding_query: GroundingQuery
    attribute_query: AttributeQuery

class EvalRequest(BaseModel):
    input_image: InputImage
    queries: EvalQueries

# Authentication Dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_current_user_optional(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not credentials:
        guest_id = request.headers.get('X-Guest-Id')
        if guest_id: return f"guest:{guest_id}"
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except Exception:
        guest_id = request.headers.get('X-Guest-Id')
        if guest_id: return f"guest:{guest_id}"
        return None


# --- HELPER FUNCTIONS ---

def encode_image_source(image_source) -> str:
    """Helper to convert bytes or string to base64 data URI"""
    try:
        if isinstance(image_source, bytes):
            encoded = base64.b64encode(image_source).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
        elif isinstance(image_source, str):
            if "base64," in image_source:
                return image_source
            else:
                return f"data:image/png;base64,{image_source}"
    except Exception as e:
        print(f"Error encoding image: {e}")
        return ""

def query_geospatial_model(image_source, prompt: str):
    """
    Sends image to SAM-Geo container (Port 2422) and returns (Class Name, Bounding Boxes).
    """
    url = "http://172.26.0.251:2422/run/predict"
    
    print(f"\n[GEO-SAM] 🚀 Preparing Request to: {url}", flush=True)
    
    base64_image = encode_image_source(image_source)
    payload = {
        "data": [
            base64_image,
            prompt
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            resp_json = response.json()
            
            # 1. Gradio API always wraps results in a "data" list
            if "data" in resp_json:
                output_data = resp_json["data"][0]
                
                # 2. Handle File Path vs Direct Object
                # (Gradio might return a file path if the JSON is large)
                print(f"h004geo_output{output_data}",flush=True)
                final_result = None
                if isinstance(output_data, str) and os.path.exists(output_data):
                    print(f"[GEO-SAM] 📂 Reading result from file: {output_data}", flush=True)
                    with open(output_data, 'r') as f:
                        final_result = json.load(f)
                else:
                    final_result = output_data
                
                print(f"h005geo_output{final_result}",flush=True)
                # 3. Extract the 'oriented_boxes' array
                if isinstance(final_result, dict):
                    # Use the exact key from your JSON: "oriented_boxes"
                    all_boxes = final_result.get("oriented_boxes", [])
                    myCls=final_result.get("detected_class")
                    print(f"h006geo_output{all_boxes}",flush=True)
                    return myCls,all_boxes  # Returns [[x1,y1...], [x1,y1...]]
                
                else:
                    print("[GEO-SAM] ⚠️ Unknown data format received inside data[0].")
                    return []

            else:
                print("[GEO-SAM] ⚠️ Response missing 'data' key", flush=True)
                return []
        else:
            print(f"[GEO-SAM] ❌ Error: {response.text}", flush=True)
            return []
            
    except Exception as e:
        print(f"[GEO-SAM] ❌ Connection Failed: {str(e)}", flush=True)
        return None, []

def query_mgm_model(image_source, prompt: str):
    """Legacy MGM Model Query"""
    print(f"\n[MGM] 🐢 Routing to MGM (Standard Model)...", flush=True)
    base64_image = encode_image_source(image_source)
    payload = {"data": [base64_image, prompt]}

    try:
        response = requests.post("http://172.26.0.251:7860/api/predict", json=payload, timeout=60)
        # response = requests.post("http://127.0.0.1:24001/api/predict", json=payload, timeout=60)
        if response.status_code == 200: return response.json()['data'][0]
        
        if response.status_code == 404:
            response = requests.post("http://172.26.0.251:7860/run/predict", json=payload, timeout=60)
            # response = requests.post("http://127.0.0.1:24001/run/predict", json=payload, timeout=60)
            if response.status_code == 200: return response.json()['data'][0]

        return f"Error from AI Server: {response.status_code}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

def query_geoChat_model(image_source, prompt: str):
    """Legacy MGM Model Query"""
    print(f"\n[MGM] 🐢 Routing to MGM (Standard Model)...", flush=True)
    base64_image = encode_image_source(image_source)
    payload = {"data": [base64_image, prompt]}

    try:
        # response = requests.post("http://127.0.0.1:7860/api/predict", json=payload, timeout=60)
        response = requests.post("http://localhost:2400/api/predict", json=payload, timeout=60)
        if response.status_code == 200: return response.json()['data'][0]
        
        if response.status_code == 404:
            # response = requests.post("http://127.0.0.1:7860/run/predict", json=payload, timeout=60)
            response = requests.post("http://localhost:24001/run/predict", json=payload, timeout=60)
            if response.status_code == 200: return response.json()['data'][0]

        return f"Error from AI Server: {response.status_code}"
    except Exception as e:
        return f"Connection Error: {str(e)}"


def find_the_class(prompt: str):
    """
    Scans the prompt to find which geospatial class is being referred to.
    Returns the specific class name required by the model, or None if not found.
    """
    
    # 1. The exact classes from your image
    valid_classes = [
        "airplane", "baseball-diamond", "bridge", "ship", "vehicle", 
        "harbor", "roundabout", "soccer-ball-field", "tennis-court", 
        "storage-tank", "ground-track-field", "swimming-pool", 
        "basketball-court", "helicopter", "airport", "container-crane", 
        "helipad", "dam", "overpass", "golffield", 
        "expressway-service-area", "chimney", "trainstation", 
        "windmill", "expressway-toll-station", "stadium"
    ]

    # 2. Map common synonyms to the official class name
    #    (e.g., user types "cars" -> we detect "vehicle")
    synonyms = {
        "plane": "airplane",
        "aeroplane": "airplane",
        "aircraft": "airplane",
        "boat": "ship",
        "vessel": "ship",
        "car": "vehicle",
        "truck": "vehicle",
        "bus": "vehicle",
        "automobiles": "vehicle",
        "port": "harbor",
        "traffic circle": "roundabout",
        "soccer field": "soccer-ball-field",
        "football field": "soccer-ball-field",
        "tennis": "tennis-court",
        "tank": "storage-tank",
        "oil tank": "storage-tank",
        "track": "ground-track-field",
        "pool": "swimming-pool",
        "basketball": "basketball-court",
        "chopper": "helicopter",
        "crane": "container-crane",
        "golf": "golffield",
        "golf course": "golffield",
        "toll station": "expressway-toll-station",
        "toll": "expressway-toll-station",
        "service area": "expressway-service-area",
        "train station": "trainstation",
        "station": "trainstation"
    }

    # Normalize prompt: lowercase and remove extra punctuation
    clean_prompt = prompt.lower().strip()
    
    # Priority 1: Check for exact matches from the official list
    # We sort by length (descending) so "soccer-ball-field" matches before just "field"
    for cls in sorted(valid_classes, key=len, reverse=True):
        # We replace hyphens with spaces for the check to be more natural 
        # (e.g., user might type "baseball diamond" instead of "baseball-diamond")
        natural_name = cls.replace("-", " ")
        
        if cls in clean_prompt or natural_name in clean_prompt:
            return cls

    # Priority 2: Check synonyms
    for keyword, official_name in synonyms.items():
        if keyword in clean_prompt:
            return official_name

    # Default: If nothing found, return None or raise error
    return None

# --- MODIFIED CONVERTER: Percentage -> Pixels ---
def convert_boxes_to_overlays(boxes, label, img_width, img_height):
    """
    Converts SAM [x1, y1, x2, y2] or [x1,xy1,x2,y2,x3,y3,x4,y4] (normalized)
    to App Overlays [{x, y, width, height, type='box'}] or [x1, y1, x2, y2] or [x1,xy1,x2,y2,x3,y3,x4,y4] IN PIXELS
    """
    overlays = []
    if not boxes: return overlays
    
    print(f"h007{boxes}",flush=True)
    print(f"[CONVERTER] Converting for Image Size: {img_width}x{img_height} pixels", flush=True)
    
    for i, box in enumerate(boxes):
        # SAM format: [x_min, y_min, x_max, y_max] in Percentages (0-100)
        if len(box) == 4:
            # Calculate Pixels
            pixel_x = (box[0] / 100) * img_width
            pixel_y = (box[1] / 100) * img_height
            
            pixel_w = ((box[2] - box[0]) / 100) * img_width
            pixel_h = ((box[3] - box[1]) / 100) * img_height
            
            overlays.append({
                "id": str(uuid.uuid4()),
                "type": "box",  # Matches your frontend expectation
                "x": int(pixel_x),
                "y": int(pixel_y),
                "width": int(pixel_w),
                "height": int(pixel_h),
                "label": label,
                "color": "#00FF00" 
            })
        elif len(box) == 8:
            overlays.append({
                "id": str(uuid.uuid4()),
                "type": "box",  # Matches your frontend expectation
                "x1": int((box[0] / 100)*img_width),
                "y1": int((box[1] / 100)*img_height),
                "x2": int((box[2] / 100)*img_width),
                "y2": int((box[3] / 100)*img_height),
                "x3": int((box[4] / 100)*img_width),
                "y3": int((box[5] / 100)*img_height),
                "x4": int((box[6] / 100)*img_width),
                "y4": int((box[7] / 100)*img_height),
                "label": label,
                "color": "#00FF00" 
            })
    return overlays

def generate_mock_overlays() -> List[dict]:
    """Generate random overlays including oriented quadrilateral boxes.
    Boxes are returned with x1..y4 instead of legacy x,y,width,height.
    Pins remain as simple x,y points.
    """
    import random
    import math
    overlays: List[dict] = []

    def random_oriented_box() -> dict:
        # Random center
        cx = random.uniform(80, 520)
        cy = random.uniform(80, 420)
        # Random size
        w = random.uniform(100, 250)
        h = random.uniform(80, 200)
        # Random orientation in radians
        theta = math.radians(random.uniform(0, 180))
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        hw, hh = w / 2.0, h / 2.0
        corners = [
            (-hw, -hh),  # top-left in local coords
            ( hw, -hh),  # top-right
            ( hw,  hh),  # bottom-right
            (-hw,  hh),  # bottom-left
        ]
        rotated = []
        for (x, y) in corners:
            rx = cx + x * cos_t - y * sin_t
            ry = cy + x * sin_t + y * cos_t
            rotated.append((rx, ry))
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = rotated
        return {
            "id": f"box-{uuid.uuid4().hex[:8]}",
            "type": "box",
            "x1": x1, "y1": y1,
            "x2": x2, "y2": y2,
            "x3": x3, "y3": y3,
            "x4": x4, "y4": y4,
            "label": random.choice(["Building", "Road", "Vegetation", "Water Body", "Structure"]),
            "color": random.choice(["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff"]),
        }

    # Random oriented boxes
    for _ in range(random.randint(1, 3)):
        overlays.append(random_oriented_box())

    # Random pins
    for _ in range(random.randint(1, 2)):
        overlays.append({
            "id": f"pin-{uuid.uuid4().hex[:8]}",
            "type": "pin",
            "x": random.uniform(100, 600),
            "y": random.uniform(100, 500),
            "label": random.choice(["POI", "Location", "Marker", "Point of Interest"]),
            "color": random.choice(["#ff8800", "#00ffff", "#8800ff"]),
        })

    return overlays

import math

def get_one_overlay(overlays):
    """
    If > 1 box:
      1. Takes the first box as reference.
      2. Finds the closest box among the remaining ones.
      3. Returns ONLY that closest box (ignoring the first one).
    """
    # 1. Safety Check: If empty or only one, return as is
    if not overlays or len(overlays) <= 1:
        return overlays

    # Helper to get center
    def get_center(box):
        cx = box['x'] + (box['width'] / 2)
        cy = box['y'] + (box['height'] / 2)
        return cx, cy


    def get_center_from_oriented_box(box):
        cx = (box['x1'] + box['x2'] + box['x3'] +box['x4'])/4
        cy = (box['y1'] + box['y2'] + box['y3'] +box['y4'])/4
        return cx, cy
    
    # 2. Extract Reference (First Box) & Candidates (The Rest)
    reference_box = overlays[0]
    remaining_boxes = overlays[1:]
    
    ref_cx, ref_cy = get_center(reference_box)

    # 3. Find the closest among the rest
    closest_box = None
    min_distance = float('inf')

    for box in remaining_boxes:
        cx, cy = get_center_from_oriented_box(box)
        
        # Euclidean Distance squared (faster and sufficient for comparison)
        dist_sq = (cx - ref_cx)**2 + (cy - ref_cy)**2
        
        if dist_sq < min_distance:
            min_distance = dist_sq
            closest_box = box

    # 4. Return ONLY the closest box
    if closest_box:
        print(f"[FILTER] Found closest neighbor to first box (DistSq: {min_distance:.0f})", flush=True)
        return [closest_box]
    
    # Fallback (should theoretically not happen given the initial check)
    return [reference_box]

def extract_overlays_from_gc_response(response_text, img_w, img_h):
    """
    Parses MGM response for pattern {<x1><y1><x2><y2>}
    Returns overlays converted to pixels.
    """
    if not response_text or not isinstance(response_text, str):
        return []

    # Regex to find: { <digits> <digits> <digits> <digits> }
    # Example: {<1><25><9><34>}
    pattern = r"\{<(\d+)><(\d+)><(\d+)><(\d+)>?\}"
    
    matches = re.findall(pattern, response_text)
    
    if not matches:
        return []

    print(f"[MGM-PARSER] Found {len(matches)} coordinate sets in response.", flush=True)
    
    sam_style_boxes = []
    
    for match in matches:
        # Convert strings '1', '25' to integers
        x1, y1, x2, y2 = map(int, match)
        sam_style_boxes.append([x1, y1, x2, y2])

    # Reuse your existing converter (it handles % -> pixel math)
    return convert_boxes_to_overlays(sam_style_boxes, "gc Detection", img_w, img_h)


def extract_overlays_from_mgm_response(response_text, img_w, img_h):
    """
    Parses MGM response for pattern {<x1><y1><x2><y2>}
    Returns overlays converted to pixels.
    """
    if not response_text or not isinstance(response_text, str):
        return []

    # Regex to find: { <digits> <digits> <digits> <digits> }
    # Example: {<1><25><9><34>}
    pattern = r"\{<(\d+)><(\d+)><(\d+)><(\d+)>?\}"
    
    matches = re.findall(pattern, response_text)
    
    if not matches:
        return []

    print(f"[MGM-PARSER] Found {len(matches)} coordinate sets in response.", flush=True)
    
    sam_style_boxes = []
    
    for match in matches:
        # Convert strings '1', '25' to integers
        x1, y1, x2, y2 = map(int, match)
        sam_style_boxes.append([x1, y1, x2, y2])

    # Reuse your existing converter (it handles % -> pixel math)
    return convert_boxes_to_overlays(sam_style_boxes, "MGM Detection", img_w, img_h)

def create_thumbnail(image_data: bytes, max_size: tuple = (150, 150)) -> str:
    img = Image.open(io.BytesIO(image_data))
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=70, optimize=True)
    buffer.seek(0)
    thumbnail_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{thumbnail_base64}"

def fix_llm_bbox_output(text_output):
    """
    Extracts the first 4 numbers from any string and formats them
    into {<n1><n2><n3><n4>}.
    """
    # 1. Regex to find all numbers (integers or floats)
    # This ignores spaces, commas, brackets, or words like "box:"
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text_output)

    # 2. Check if we found at least 4 numbers
    if len(numbers) >= 4:
        # Take the first 4 numbers
        n1, n2, n3, n4 = numbers[:4]
        
        # 3. Construct the specific format you want
        # Note: If your model requires Integers (0-100), you might want to 
        # convert them to int() here first: int(float(n1))
        return f"{{<{n1}><{n2}><{n3}><{n4}>}}"
    else:
        print(f"⚠️ Error: Could not find 4 numbers in LLM output: '{text_output}'")
        return None
    
def get_image_dimensions(image_source):
    """Extracts width and height from bytes or base64 string"""
    try:
        if isinstance(image_source, bytes):
            img = Image.open(io.BytesIO(image_source))
        elif isinstance(image_source, str):
            # Remove header if present
            if "base64," in image_source:
                encoded = image_source.split("base64,")[1]
            else:
                encoded = image_source
            img = Image.open(io.BytesIO(base64.b64decode(encoded)))
        
        return img.width, img.height
    except Exception as e:
        print(f"Error getting dimensions: {e}")
        return 1000, 1000 # Fallback to prevent crash

# --- API ENDPOINTS ---
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

@app.post("/eval")
async def eval_endpoint(payload: EvalRequest):
    """
    Processes an evaluation request, downloads the input image, and returns
    basic info with placeholders for query results. Image is downloaded to a
    temporary file; the base64 is also returned for convenience.
    """
    try:
        image_url = payload.input_image.image_url
        image_id = payload.input_image.image_id

        # Download image
        resp = requests.get(image_url, timeout=30)
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to download image: {resp.status_code}")

        image_bytes = resp.content

        img_w = payload.input_image.metadata.width
        img_h = payload.input_image.metadata.height
        
        
        
        caption_result = {
            "instruction": payload.queries.caption_query.instruction,
            "response": "Text-based description placeholder.",
        }

        grounding_result = {
            "instruction": payload.queries.grounding_query.instruction,
            "response": []
        }

        attribute_result = {
            "binary": {
                "instruction": payload.queries.attribute_query.binary.instruction,
                "response": "Unknown"
            },
            "numeric": {
                "instruction": payload.queries.attribute_query.numeric.instruction,
                "response": None
            },
            "semantic": {
                "instruction": payload.queries.attribute_query.semantic.instruction,
                "response": "Not implemented"
            }
        }

        # Return combined response
        return JSONResponse(
            content={
                "image": {
                    "image_id": image_id,
                    "dimensions": {"width": img_w, "height": img_h},
                    "spatial_resolution_m": payload.input_image.metadata.spatial_resolution_m,
                },
                "queries": {
                    "caption_query": caption_result,
                    "grounding_query": grounding_result,
                    "attribute_query": attribute_result
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /eval failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_image(
    image: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        session_id = str(uuid.uuid4())
        image_data = await image.read()
        
        # Get Real Dimensions for Pixel Conversion
        img_w, img_h = get_image_dimensions(image_data)
        
        image_base64 = f"data:{image.content_type};base64,{base64.b64encode(image_data).decode()}"
        thumbnail = create_thumbnail(image_data)
        
        initial_response = "Image uploaded successfully!"
        overlays = []

        if prompt:
            raw_prompt = prompt
            prompt = raw_prompt.strip()
            print(f"\n[UPLOAD] Checking Prompt: '{prompt}'", flush=True)

            starts_with_quote = prompt.startswith('"') or prompt.startswith('“')
            ends_with_quote = prompt.endswith('"') or prompt.endswith('”')

            if starts_with_quote and ends_with_quote:
                print("[UPLOAD] 👉 Condition MET: Using GEOSPATIAL MODEL", flush=True)
                clean_prompt = prompt[1:-1]
                
                # Query SAM (Returns %)
                new_cls,boxes = query_geospatial_model(image_data, clean_prompt)
                
                # Convert % to Pixels using img_w/img_h
                overlays = convert_boxes_to_overlays(boxes, new_cls, img_w, img_h)
                
                count = len(overlays)
                initial_response = f"Geospatial Analysis complete. Found {count} instances of '{new_cls}'."
            else:
                print("[UPLOAD] 👉 Condition FAILED: Using MGM MODEL", flush=True)
                initial_response = query_mgm_model(image_data, prompt)
                # overlays = generate_mock_overlays()
                overlays = []
                # Check for {<x><y><x><y>} pattern
                if initial_response and "{" in initial_response and "<" in initial_response:
                    # overlays = extract_overlays_from_mgm_response(initial_response, img_w, img_h)
                    overlays=[]
                    # new_class=find_the_class(prompt)
                    # if new_class:
                    #     print(f"[HYBRID] Detected class '{new_class}', querying Geo-SAM...", flush=True)
                    new_cls,new_boxes = query_geospatial_model(image_data, prompt)
                    

                    new_prompt_for_bb = "give bounding box for " + prompt
                    new_bb_from_gc=query_geoChat_model(image_data, new_prompt_for_bb)
                    # new_bb_from_gc=new_bb_from_gc[0:-1]+">}"
                    new_bb_from_gc = fix_llm_bbox_output(new_bb_from_gc)

                    print(f"[CHAT] 👉 geoChat={new_bb_from_gc}", flush=True)
                    new_gc_overlay= extract_overlays_from_gc_response(new_bb_from_gc, img_w, img_h)
                    overlays.extend(new_gc_overlay)
                
                    # Convert new boxes to overlay format
                    sam_overlays = convert_boxes_to_overlays(new_boxes, new_cls, img_w, img_h)
                    
                    # --- FIX: Use extend to flatten the list ---
                    overlays.extend(sam_overlays)
                    if len(overlays) > 1:
                        overlays = get_one_overlay(overlays)

        else:
            overlays = generate_mock_overlays()
        
        # Save to DB
        messages_to_insert = []
        if prompt:
            messages_to_insert = [
                {
                    "messageId": str(uuid.uuid4()), "sessionId": session_id, "from": "user",
                    "text": prompt, "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "messageId": str(uuid.uuid4()), "sessionId": session_id, "from": "ai",
                    "text": initial_response, "timestamp": datetime.now(timezone.utc).isoformat()
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
        
        if user_id:
            session_doc = {
                "sessionId": session_id, "userId": user_id, "thumbnail": thumbnail,
                "initialPrompt": prompt or "", "messageCount": len(messages_to_insert),
                "createdAt": datetime.now(timezone.utc).isoformat(), "updatedAt": datetime.now(timezone.utc).isoformat()
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
        print(f"[ERROR] upload_image failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def send_message(
    chat_message: ChatMessage,
    user_id: Optional[str] = Depends(get_current_user_optional)
):
    try:
        if user_id:
            session = await db.sessions.find_one({"sessionId": chat_message.sessionId, "userId": user_id})
            if not session: raise HTTPException(status_code=404, detail="Session not found")

        image_to_process = chat_message.imageUrl
        if not image_to_process:
            image_doc = await db.images.find_one({"sessionId": chat_message.sessionId})
            if image_doc:
                image_to_process = image_doc.get("imageUrl")
        
        new_overlays = []
        ai_response = ""
        prompt = chat_message.message.strip()

        print(f"\n[CHAT] Processing: '{prompt}'", flush=True)

        if not image_to_process:
            ai_response = "Error: Cannot find image context for this session."
        else:
            starts_with_quote = prompt.startswith('"') or prompt.startswith('“')
            ends_with_quote = prompt.endswith('"') or prompt.endswith('”')

            if starts_with_quote and ends_with_quote:
                print("[CHAT] 👉 Condition MET: Using GEOSPATIAL MODEL", flush=True)
                clean_prompt = prompt[1:-1]
                
                # Get Dimensions from Base64 string for Pixel Conversion
                img_w, img_h = get_image_dimensions(image_to_process)
                
                # Query SAM
                new_cls,boxes = query_geospatial_model(image_to_process, clean_prompt)
                
                # Convert to Pixels
                new_overlays = convert_boxes_to_overlays(boxes, new_cls, img_w, img_h)
                
                print(f"h008{new_overlays}",flush=True)
                count = len(new_overlays)
                ai_response = f"Found {count} instances of '{new_cls}'."
                
                if new_overlays:
                    await db.images.update_one(
                        {"sessionId": chat_message.sessionId},
                        {"$set": {"overlays": new_overlays}}
                    )
            else:
                print("[CHAT] 👉 Condition FAILED: Using MGM MODEL", flush=True)
                ai_response = query_mgm_model(image_to_process, prompt)
                if ai_response and "{" in ai_response and "<" in ai_response:
                    # Ensure img_w/img_h are calculated
                    if 'img_w' not in locals(): 
                        img_w, img_h = get_image_dimensions(image_to_process)
                        
                    # new_overlays = extract_overlays_from_mgm_response(ai_response, img_w, img_h)
                    new_overlays =[]
                    new_prompt_for_bb = "give bounding box for " + prompt
                    new_bb_from_gc=query_geoChat_model(image_to_process, new_prompt_for_bb)
                    # new_bb_from_gc=new_bb_from_gc[0:-1]+">}"
                    new_bb_from_gc = fix_llm_bbox_output(new_bb_from_gc)
                    print(f"[CHAT] 👉 geoChat={new_bb_from_gc}", flush=True)
                    new_gc_overlay= extract_overlays_from_gc_response(new_bb_from_gc, img_w, img_h)
                    new_overlays.extend(new_gc_overlay)
                    # new_class=find_the_class(prompt)
                    # if new_class:
                    # print(f"[HYBRID] Detected class '{new_class}', querying Geo-SAM...", flush=True)
                    print(f"h000{new_overlays}",flush=True)
                    new_cls,new_boxes = query_geospatial_model(image_to_process, prompt)
                    
                    # print(new_boxes, new_overlays)
                    print(f"h001{new_boxes}",flush=True)
                    # Convert new boxes to overlay format
                    sam_overlays = convert_boxes_to_overlays(new_boxes, new_cls, img_w, img_h)
                    
                    print(f"h002{sam_overlays}",flush=True)
                    # --- FIX: Use extend to flatten the list ---
                    new_overlays.extend(sam_overlays)
                    if len(new_overlays) > 1:
                        new_overlays = get_one_overlay(new_overlays)
                    print(f"new overlays:{new_overlays}", flush=True)

                if new_overlays:
                    await db.images.update_one(
                        {"sessionId": chat_message.sessionId},
                        {"$set": {"overlays": new_overlays}}
                    )

        messages_to_insert = [
            {
                "messageId": str(uuid.uuid4()), "sessionId": chat_message.sessionId, "from": "user",
                "text": chat_message.message, "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "messageId": str(uuid.uuid4()), "sessionId": chat_message.sessionId, "from": "ai",
                "text": ai_response, "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        await db.messages.insert_many(messages_to_insert)
        
        if user_id:
            await db.sessions.update_one(
                {"sessionId": chat_message.sessionId},
                {"$set": {"updatedAt": datetime.now(timezone.utc).isoformat()}, "$inc": {"messageCount": 2}}
            )
        
        return {"message": ai_response, "overlays": new_overlays}
    
    except Exception as e:
        print(f"[ERROR] Chat failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
async def create_session(
    session_data: CreateSession,
    user_id: str = Depends(get_current_user)
):
    try:
        session_id = str(uuid.uuid4())
        initial_response = ""
        raw_prompt = session_data.initialPrompt
        prompt = raw_prompt.strip()
        overlays = [] 

        print(f"\n[SESSION] Checking: '{prompt}'", flush=True)

        starts_with_quote = prompt.startswith('"') or prompt.startswith('“')
        ends_with_quote = prompt.endswith('"') or prompt.endswith('”')

        if starts_with_quote and ends_with_quote:
            print("[SESSION] 👉 Using GEOSPATIAL MODEL", flush=True)
            clean_prompt = prompt[1:-1]
            
            # Get Dimensions
            img_w, img_h = get_image_dimensions(session_data.imageUrl)
            
            new_cls,boxes = query_geospatial_model(session_data.imageUrl, clean_prompt)
            
            overlays = convert_boxes_to_overlays(boxes, new_cls, img_w, img_h)
            
            count = len(overlays)
            initial_response = f"Geospatial Analysis complete. Found {count} instances of '{new_cls}'."
        else:
            print("[SESSION] 👉 Using MGM MODEL", flush=True)
            initial_response = query_mgm_model(session_data.imageUrl, prompt)
            overlays = []
            if initial_response and "{" in initial_response and "<" in initial_response:
                 # Ensure dimensions are calculated
                 img_w, img_h = get_image_dimensions(session_data.imageUrl)
                 overlays = extract_overlays_from_mgm_response(initial_response, img_w, img_h)
                 
                 new_prompt_for_bb = "give bounding box for " + prompt
                 new_bb_from_gc=query_geoChat_model(session_data.imageUrl, new_prompt_for_bb)
                #  new_bb_from_gc=new_bb_from_gc[0:-1]+">}"
                 new_bb_from_gc = fix_llm_bbox_output(new_bb_from_gc)
                 print(f"[CHAT] 👉 geoChat={new_bb_from_gc}", flush=True)
                 new_gc_overlay= extract_overlays_from_gc_response(new_bb_from_gc, img_w, img_h)
                 overlays.extend(new_gc_overlay)
                #  new_class=find_the_class(prompt)
                #  if new_class:
                #     print(f"[HYBRID] Detected class '{new_class}', querying Geo-SAM...", flush=True)
                 new_cls,new_boxes = query_geospatial_model(session_data.imageUrl, prompt)
                
                # Convert new boxes to overlay format
                 sam_overlays = convert_boxes_to_overlays(new_boxes, new_cls, img_w, img_h)
                
                # --- FIX: Use extend to flatten the list ---
                 overlays.extend(sam_overlays)
                #  if len(overlays) > 1:
                #     overlays = get_one_overlay(overlays)
                        
        messages_to_insert = [
            { "messageId": str(uuid.uuid4()), "sessionId": session_id, "from": "user", "text": prompt, "timestamp": datetime.now(timezone.utc).isoformat() },
            { "messageId": str(uuid.uuid4()), "sessionId": session_id, "from": "ai", "text": initial_response, "timestamp": datetime.now(timezone.utc).isoformat() }
        ]
        
        await db.messages.insert_many(messages_to_insert)
        
        thumbnail = session_data.imageUrl
        if session_data.imageUrl.startswith('data:image'):
            header, encoded = session_data.imageUrl.split(',', 1)
            image_data_bytes = base64.b64decode(encoded)
            thumbnail = create_thumbnail(image_data_bytes)
        
        image_doc = {
            "sessionId": session_id, "imageUrl": session_data.imageUrl,
            "overlays": overlays, "createdAt": datetime.now(timezone.utc).isoformat()
        }
        await db.images.insert_one(image_doc)
        
        session_doc = {
            "sessionId": session_id, "userId": user_id, "thumbnail": thumbnail,
            "initialPrompt": prompt, "messageCount": 2,
            "createdAt": datetime.now(timezone.utc).isoformat(), "updatedAt": datetime.now(timezone.utc).isoformat()
        }
        await db.sessions.insert_one(session_doc)
        
        return {
            "sessionId": session_id, "imageUrl": session_data.imageUrl,
            "thumbnail": thumbnail, "initialResponse": initial_response, "overlays": overlays
        }
    
    except Exception as e:
        print(f"[ERROR] create_session failed: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/browser-test")
def browser_test(name: str, age: int, message: str):
    """
    Allows testing via browser address bar using Query Parameters.
    URL format: /browser-test?name=John&age=30&message=Hello
    """
    # Create the dictionary (JSON) to return
    response_data = {
        "status": "success",
        "received_data": {
            "name": name,
            "age": age,
            "message": message
        },
        "note": "This was a GET request directly from the browser!"
    }
    return response_data


# ... (Keep get_chat_history, get_sessions, get_session_image, delete_session EXACTLY as they were) ...
@app.get("/api/chat/{session_id}")
async def get_chat_history(session_id: str, user_id: Optional[str] = Depends(get_current_user_optional)):
    try:
        if user_id:
            session = await db.sessions.find_one({"sessionId": session_id, "userId": user_id})
            if not session: raise HTTPException(status_code=404, detail="Session not found")
        messages = await db.messages.find({"sessionId": session_id}, {"_id": 0, "messageId": 1, "from": 1, "text": 1, "timestamp": 1}).sort("timestamp", 1).to_list(1000)
        for msg in messages: msg["id"] = msg.pop("messageId")
        return {"messages": messages}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_sessions(user_id: Optional[str] = Depends(get_current_user_optional)):
    try:
        if not user_id: raise HTTPException(status_code=401, detail="Not authenticated")
        sessions = await db.sessions.find({"userId": user_id}, {"_id": 0, "sessionId": 1, "thumbnail": 1, "initialPrompt": 1, "createdAt": 1, "updatedAt": 1, "messageCount": 1}).sort("updatedAt", -1).to_list(100)
        return {"sessions": sessions}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/image")
async def get_session_image(session_id: str, user_id: Optional[str] = Depends(get_current_user_optional)):
    try:
        if user_id:
            session = await db.sessions.find_one({"sessionId": session_id, "userId": user_id}, {"_id": 0})
            if not session: raise HTTPException(status_code=404, detail="Session not found")
        image_data = await db.images.find_one({"sessionId": session_id}, {"_id": 0, "imageUrl": 1, "overlays": 1})
        if not image_data: raise HTTPException(status_code=404, detail="Image not found")
        return {"imageUrl": image_data.get("imageUrl"), "overlays": image_data.get("overlays", [])}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Depends(get_current_user)):
    try:
        result = await db.sessions.delete_one({"sessionId": session_id, "userId": user_id})
        if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Session not found")
        await db.messages.delete_many({"sessionId": session_id})
        await db.images.delete_one({"sessionId": session_id})
        return {"success": True, "message": "Session deleted"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

## EVAL MODE 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
