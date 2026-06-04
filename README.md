# GeoNLI: Geospatial Intelligence Chat Platform

**Inter IIT Tech Meet 14.0 - ISRO Challenge | Team 99**

GeoNLI is a full-stack web application that combines satellite imagery analysis with conversational AI. Users can upload geospatial images, interact with an AI-powered assistant to analyze them, and generate visual overlays (bounding boxes and pins) to annotate regions of interest.

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Setup and Installation](#setup-and-installation)
- [Running the Application](#running-the-application)
- [Development Guide](#development-guide)
- [API Documentation](#api-documentation)
- [Features](#features)

## 🎯 Overview

GeoNLI leverages geospatial intelligence by:
1. **Image Upload**: Users upload satellite or geospatial images
2. **AI Analysis**: A machine learning model (via Gradio) analyzes images and generates insights
3. **Interactive Chat**: Users can ask follow-up questions about the image in a chat interface
4. **Visual Annotations**: Generate and manage overlays (boxes and pins) to highlight areas of interest
5. **Session Management**: Maintain persistent chat history and image metadata

The application supports both authenticated users (via JWT) and anonymous guests, allowing flexible access to geospatial intelligence tools.

## 📁 Project Structure

```
geonli/
├── README.md                    # This file
├── ck.py                        # Test client for Gradio integration
├── backend/                     # FastAPI backend service
│   ├── main.py                  # Main FastAPI application
│   ├── requirements.txt         # Python dependencies
│   ├── docker-compose.yml       # Docker orchestration
│   ├── Dockerfile               # Backend container definition
│   ├── geonli.json              # Configuration file
│   ├── README.md                # Backend-specific documentation
│   └── mongo-init/              # MongoDB initialization scripts
│       └── 01-init.js           # Init database and user
├── frontend/                    # React + Vite frontend
│   ├── package.json             # Node dependencies
│   ├── vite.config.js           # Vite configuration
│   ├── tailwind.config.js       # Tailwind CSS configuration
│   ├── firebase.json            # Firebase deployment config
│   ├── index.html               # HTML entry point
│   ├── README.md                # Frontend-specific documentation
│   └── src/
│       ├── main.jsx             # React entry point
│       ├── App.jsx              # Root component
│       ├── index.css            # Global styles
│       ├── contexts/            # React context providers
│       │   ├── AuthContext.jsx   # Authentication state
│       │   └── ThemeContext.jsx  # Theme state management
│       ├── pages/               # Page components
│       │   ├── LoginPage.jsx     # Login/signup interface
│       │   ├── UploadPage.jsx    # Image upload interface
│       │   └── ChatPage.jsx      # Chat and image analysis
│       ├── components/          # Reusable UI components
│       │   ├── Topbar.jsx        # Navigation header
│       │   ├── LeftSidebar.jsx   # Session history sidebar
│       │   ├── ChatPanel.jsx     # Chat message display
│       │   ├── ImageViewer.jsx   # Image viewer with overlays
│       │   └── icons/            # SVG icon components
│       └── services/
│           └── api.js           # HTTP client and API calls
└── .git                         # Git version control
```

## 🛠️ Technology Stack

### Frontend
- **React 18**: UI framework
- **Vite**: Lightning-fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API requests
- **React Zoom Pan Pinch**: Interactive image viewer
- **React Transition Group**: Smooth animations

### Backend
- **FastAPI**: Modern Python async web framework
- **Uvicorn**: ASGI server for FastAPI
- **Motor**: Async MongoDB driver
- **PyJWT**: JWT token generation and validation
- **Passlib + bcrypt**: Password hashing and validation
- **Pillow**: Image processing and manipulation
- **Gradio Client**: Integration with ML model service
- **Firebase Admin SDK**: Cloud authentication and storage

### Infrastructure
- **MongoDB**: NoSQL database for storing sessions, messages, images
- **Docker & Docker Compose**: Containerization and orchestration
- **Firebase Hosting**: Deployment platform for frontend

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Port 3000)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Pages: Login | Upload | Chat                       │   │
│  │  Components: TopBar | Sidebar | Chat | ImageViewer  │   │
│  │  State: AuthContext (JWT/Guest) | ThemeContext     │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────┬──────────────────────────────────────────────┘
               │ HTTP(S) + JWT/Guest Headers
               ↓
┌──────────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Auth Endpoints: /signup, /login                    │    │
│  │  Image Endpoints: /upload, /sessions/{id}/image     │    │
│  │  Chat Endpoints: /chat, /chat/{session_id}         │    │
│  │  Session Endpoints: /sessions, /sessions/{id}      │    │
│  └─────────────────────────────────────────────────────┘    │
└──────┬───────────────┬──────────────────┬───────────────────┘
       │               │                  │
       ↓               ↓                  ↓
┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│  MongoDB    │  │ Gradio Model │  │ Image Storage  │
│  (Sessions, │  │ (ML Analysis)│  │ (Data URLs)    │
│  Messages,  │  │              │  │                │
│  Users)     │  │              │  │                │
└─────────────┘  └──────────────┘  └────────────────┘
```

### Data Model

**Users Collection**
```json
{
  "_id": "ObjectId",
  "email": "user@example.com",
  "password_hash": "bcrypt_hash",
  "createdAt": "timestamp"
}
```

**Sessions Collection**
```json
{
  "sessionId": "uuid",
  "userId": "user_id | guest_id",
  "thumbnail": "data_url",
  "initialPrompt": "user's initial question",
  "messageCount": 5,
  "createdAt": "timestamp",
  "updatedAt": "timestamp"
}
```

**Messages Collection**
```json
{
  "messageId": "uuid",
  "sessionId": "session_uuid",
  "from": "user | ai",
  "text": "message content",
  "timestamp": "timestamp"
}
```

**Images Collection**
```json
{
  "sessionId": "session_uuid",
  "imageUrl": "data:image/png;base64,...",
  "overlays": [
    {
      "id": "overlay_id",
      "type": "box | pin",
      "x": 100, "y": 150, "width": 200, "height": 300,
      "label": "Building",
      "color": "#FF0000"
    }
  ],
  "createdAt": "timestamp"
}
```

## 🚀 Setup and Installation

### Prerequisites
- Node.js 16+ (for frontend)
- Python 3.9+ (for backend)
- Docker & Docker Compose (for containerized setup)
- MongoDB 5.0+ (or use Docker Compose)

### Environment Configuration

#### Backend (.env in backend/)
```
MONGODB_URL=******localhost:27017/geonli?authSource=geonli
JWT_SECRET=your-secret-key-here
```

#### Frontend (.env in frontend/)
```
VITE_API_URL=http://localhost:8000
```

### Installation Steps

**Option 1: Using Docker Compose (Recommended)**

```bash
# Navigate to backend directory
cd backend

# Start all services (MongoDB + FastAPI)
docker compose up -d

# Frontend runs separately
cd ../frontend
npm install
npm run dev
```

**Option 2: Local Development Setup**

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Ensure MongoDB is running locally or update MONGODB_URL

# Start backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (in separate terminal)
cd frontend
npm install
npm run dev
```

## ▶️ Running the Application

### With Docker Compose (Full Stack)

```bash
cd backend
docker compose up -d

# Backend: http://localhost:8000
# MongoDB: localhost:27017
# Frontend: http://localhost:3000 (run npm run dev separately)
```

### Development Servers

```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Gradio Model Service (if available)
# Run your ML model on port 7860
```

### Production Build

```bash
# Build frontend
cd frontend
npm run build
npm run preview

# Deploy backend to production (e.g., Docker container to cloud)
```

## 💻 Development Guide

### Backend Development

**Project Structure**: See `/backend/README.md` for detailed backend documentation.

**Key Files**:
- `main.py`: All routes, models, and business logic
- `requirements.txt`: Python dependencies

**Running Tests**:
```bash
# Backend testing (if tests are added)
pytest backend/
```

**Adding New Endpoints**:
1. Define Pydantic model in `main.py`
2. Create route function with appropriate decorators
3. Implement business logic (DB queries, ML integration)
4. Return JSON response

### Frontend Development

**Project Structure**: See `/frontend/README.md` for detailed frontend documentation.

**Key Files**:
- `src/App.jsx`: Main component and routing
- `src/contexts/`: Global state (Auth, Theme)
- `src/services/api.js`: API integration layer
- `src/components/`: Reusable UI components

**Development Workflow**:
```bash
cd frontend
npm run dev              # Start dev server
npm run lint            # Check code quality
npm run build           # Production build
```

**Key Commands**:
- `npm run dev` - Start Vite dev server (HMR enabled)
- `npm run build` - Create production bundle
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint checks

### Adding Features

1. **New API Endpoint**:
   - Add Pydantic model in backend
   - Create FastAPI route handler
   - Test with cURL or Postman
   - Implement frontend component/page
   - Update api.js with new client method

2. **New UI Component**:
   - Create component in `src/components/`
   - Add to parent component or page
   - Update styles with Tailwind CSS
   - Use existing context if needed for state

3. **Authentication**:
   - Frontend: Uses `geonli_token` in localStorage (JWT)
   - Backend: Validates token in Authorization header
   - Guest Mode: Uses `X-Guest-Id` header with stable UUID

## 📚 API Documentation

For detailed API documentation, see `/backend/README.md`.

### Key Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | No | Create account and get JWT |
| POST | `/api/auth/login` | No | Login and get JWT |
| POST | `/api/upload` | Optional | Upload image and create session |
| POST | `/api/chat` | Optional | Send message in chat session |
| GET | `/api/chat/{session_id}` | Optional | Fetch chat history |
| GET | `/api/sessions` | Required | List user sessions |
| POST | `/api/sessions` | Required | Create session from image URL |
| GET | `/api/sessions/{id}/image` | Optional | Get image and overlays |
| DELETE | `/api/sessions/{id}` | Required | Delete session |

## ✨ Features

### Core Features
- ✅ User authentication (signup/login with JWT)
- ✅ Guest mode (persistent anonymous access)
- ✅ Image upload with automatic thumbnail generation
- ✅ AI-powered image analysis via Gradio
- ✅ Multi-turn conversational chat
- ✅ Overlay annotations (boxes and pins)
- ✅ Session management and history
- ✅ Responsive UI with Tailwind CSS

### Technical Features
- ✅ Async backend with FastAPI
- ✅ NoSQL database with MongoDB
- ✅ JWT-based authentication
- ✅ CORS support for cross-origin requests
- ✅ Image processing and manipulation
- ✅ Docker containerization
- ✅ Hot module reloading (HMR) in development
- ✅ Firebase deployment ready

## 📝 License and Credits

**Inter IIT Tech Meet 14.0** - ISRO Geospatial Intelligence Challenge
**Team 99**

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and test thoroughly
3. Commit with clear messages: `git commit -m "Add feature description"`
4. Push to your branch: `git push origin feature/your-feature`
5. Open a pull request

## 📞 Support

For issues, questions, or contributions, please refer to the specific documentation:
- **Backend Issues**: See `/backend/README.md`
- **Frontend Issues**: See `/frontend/README.md`
- **Deployment**: Check Docker Compose configuration and Firebase settings
