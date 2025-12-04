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
import firebase_admin
from firebase_admin import credentials, auth
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image
import io
import base64
import tempfile
from gradio_client import Client, handle_file
import requests
import json
import re
import math

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
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.geonli

# Firebase Admin Configuration
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)

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
    type: str
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    label: Optional[str] = None
    color: Optional[str] = None


class UserData(BaseModel):
    name: str
    age: int
    message: str

# --- 2. DEFINE THE ENDPOINT ---
@app.post("/process-user-data")
async def echo_data(data: UserData):
    """
    Reads the JSON sent by frontend and returns it exactly as is.
    """
    print(f"Received data: {data}")
    return data 


# --- Dependencies ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_current_user_optional(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    if not credentials:
        guest_id = request.headers.get('X-Guest-Id')
        if guest_id: return f"guest:{guest_id}"
        return None
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
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
    url = "http://localhost:2422/run/predict"
    
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
            
            if "data" in resp_json:
                output_data = resp_json["data"][0]
                
                # --- 1. Handle File Path vs Direct Object ---
                # Gradio might return a file path string or the direct dictionary
                final_result = None
                
                if isinstance(output_data, str) and os.path.exists(output_data):
                    print(f"[GEO-SAM] 📂 Reading result from file: {output_data}", flush=True)
                    with open(output_data, 'r') as f:
                        final_result = json.load(f)
                else:
                    final_result = output_data
                
                # --- 2. Extract Class and Boxes ---
                # We expect final_result to be: {'detected_class': '...', 'boxes': [...]}
                if isinstance(final_result, dict):
                    detected_class = final_result.get("detected_class", prompt) # Fallback to prompt if key missing
                    boxes = final_result.get("boxes", [])
                    return detected_class, boxes
                
                # Fallback: If server sends just a list (Old format safety net)
                elif isinstance(final_result, list):
                    print("[GEO-SAM] ⚠️ Warning: Received list format. Using prompt as class.")
                    return prompt, final_result
                
                else:
                    print("[GEO-SAM] ⚠️ Unknown data format received.")
                    return None, []

            else:
                print("[GEO-SAM] ⚠️ Response missing 'data' key", flush=True)
                return None, []
        else:
            print(f"[GEO-SAM] ❌ Error: {response.text}", flush=True)
            return None, []
            
    except Exception as e:
        print(f"[GEO-SAM] ❌ Connection Failed: {str(e)}", flush=True)
        return None, []

def query_mgm_model(image_source, prompt: str):
    """Legacy MGM Model Query"""
    print(f"\n[MGM] 🐢 Routing to MGM (Standard Model)...", flush=True)
    base64_image = encode_image_source(image_source)
    payload = {"data": [base64_image, prompt]}

    try:
        response = requests.post("http://127.0.0.1:7860/api/predict", json=payload, timeout=60)
        # response = requests.post("http://127.0.0.1:24001/api/predict", json=payload, timeout=60)
        if response.status_code == 200: return response.json()['data'][0]
        
        if response.status_code == 404:
            response = requests.post("http://127.0.0.1:7860/run/predict", json=payload, timeout=60)
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
        response = requests.post("http://127.0.0.1:24001/api/predict", json=payload, timeout=60)
        if response.status_code == 200: return response.json()['data'][0]
        
        if response.status_code == 404:
            # response = requests.post("http://127.0.0.1:7860/run/predict", json=payload, timeout=60)
            response = requests.post("http://127.0.0.1:24001/run/predict", json=payload, timeout=60)
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
    Converts SAM [x1, y1, x2, y2] (0-100 normalized) 
    to App Overlays [{x, y, width, height, type='box'}] IN PIXELS
    """
    overlays = []
    if not boxes: return overlays
    
    print(f"[CONVERTER] Converting for Image Size: {img_width}x{img_height} pixels", flush=True)
    
    for i, box in enumerate(boxes):
        # SAM format: [x_min, y_min, x_max, y_max] in Percentages (0-100)
        p_x1, p_y1, p_x2, p_y2 = box
        
        # Calculate Pixels
        pixel_x = (p_x1 / 100) * img_width
        pixel_y = (p_y1 / 100) * img_height
        
        pixel_w = ((p_x2 - p_x1) / 100) * img_width
        pixel_h = ((p_y2 - p_y1) / 100) * img_height
        
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

    # 2. Extract Reference (First Box) & Candidates (The Rest)
    reference_box = overlays[0]
    remaining_boxes = overlays[1:]
    
    ref_cx, ref_cy = get_center(reference_box)

    # 3. Find the closest among the rest
    closest_box = None
    min_distance = float('inf')

    for box in remaining_boxes:
        cx, cy = get_center(box)
        
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

def generate_mock_overlays(img_width=800, img_height=600) -> List[dict]:
    """
    Generates a single fixed box in the center of the image.
    Defaults to 800x600 if dimensions are not provided.
    """
    import uuid
    
    # 1. Define the Fixed Box Size
    box_w = 200
    box_h = 200
    
    # 2. Calculate Center Coordinates
    # Center X = (Image Width / 2) - (Box Width / 2)
    center_x = (img_width / 2) - (box_w / 2)
    center_y = (img_height / 2) - (box_h / 2)
    
    return [{
        "id": str(uuid.uuid4()),
        "type": "box",
        "x": int(center_x),
        "y": int(center_y),
        "width": box_w,
        "height": box_h,
        "label": "Mock Center",
        "color": "#FF0000" # Red for visibility
    }]

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
                    overlays = extract_overlays_from_mgm_response(initial_response, img_w, img_h)
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
                    # if len(overlays) > 1:
                    #     overlays = get_one_overlay(overlays)

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
                        
                    new_overlays = extract_overlays_from_mgm_response(ai_response, img_w, img_h)

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
                    new_cls,new_boxes = query_geospatial_model(image_to_process, prompt)
                    
                    # Convert new boxes to overlay format
                    sam_overlays = convert_boxes_to_overlays(new_boxes, new_cls, img_w, img_h)
                    
                    # --- FIX: Use extend to flatten the list ---
                    new_overlays.extend(sam_overlays)
                    # if len(new_overlays) > 1:
                    #     new_overlays = get_one_overlay(new_overlays)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)