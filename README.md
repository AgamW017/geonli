# Inter IIT 14.0 - ISRO (GeoSpacial Intelligence)
# Geonli — Full Setup Guide (Backend + Frontend + Firebase + MongoDB)

# ---------------------------------------------
# 1. Create and activate Conda environment
# ---------------------------------------------
conda create -n env_geonli python=3.11 -y
conda activate env_geonli

# ---------------------------------------------
# 2. Backend setup
# ---------------------------------------------
cd D:\InterIIT\geonli\backend

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install six pygments

# ---------------------------------------------
# 3. Add Firebase Admin SDK key
# ---------------------------------------------


# Set env vars (temporary for this session)
same as .env of backend
(only if it is not working already)
$env:FIREBASE_CREDENTIALS_PATH=""
$env:MONGO_URL=""

# ---------------------------------------------
# 4. Run the backend
# ---------------------------------------------
uvicorn main:app --reload
# Backend URL → http://127.0.0.1:8000

# ---------------------------------------------
# 5. Frontend setup
# ---------------------------------------------
cd D:\InterIIT\geonli\frontend

# Create frontend/.env

# Install frontend dependencies
npm install

# Run frontend
npm run dev
# Frontend URL → http://localhost:3000
