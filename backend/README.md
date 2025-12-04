# GeoNLI Backend

FastAPI backend providing image upload, ... [insert later], session management, and MongoDB persistence. Supports authenticated users via JWT and persistent guests via `X-Guest-Id`.

## Tech Stack
- FastAPI (async)
- Uvicorn
- MongoDB (Motor async driver)
- JWT auth (`PyJWT`)
- Password hashing (`passlib[bcrypt]`)
- Image processing (`Pillow`)

## File Structure
```
backend/
  Dockerfile
  docker-compose.yml
  main.py
  requirements.txt
  mongo-data/              # MongoDB data volume
  mongo-init/              # MongoDB init scripts
    01-init.js
```

## Environment Variables
The app reads from `.env` and Docker env.
- `JWT_SECRET` 
(leave empty for default)

## Running with Docker Compose
`docker-compose.yml` provisions MongoDB and the backend.

```
# From backend/
docker compose up -d
```
- Backend: `http://localhost:8000`
- MongoDB: `localhost:27017` (container `geonli-mongo`)

## CORS
Allowed origin: `http://localhost:3000`.

## Authentication
- JWT via `Authorization: Bearer <token>` (issued on signup/login).
- Guests: If no token, send `X-Guest-Id: <stable-uuid>` header. Many endpoints work for guests; some require auth.

### JWT Details
- Algorithm: HS256
- Claims: `sub` (user id), `iat`, `exp`

## Data Model (MongoDB Collections)
- `users`: `{ _id, email, password_hash, createdAt }`
- `sessions`: `{ sessionId, userId, thumbnail, initialPrompt, messageCount, createdAt, updatedAt }`
- `messages`: `{ messageId, sessionId, from: 'user'|'ai', text, timestamp }`
- `images`: `{ sessionId, imageUrl (data URL), overlays: [ ... ], createdAt }`

`overlays` are simple objects:
- Box: `{ id, type: 'box', x, y, width, height, label, color }`
- Pin: `{ id, type: 'pin', x, y, label, color }`

## API Endpoints
Base URL: `http://localhost:8000`

### GET `/`
Health check.

### POST `/api/auth/signup`
Signup and receive token.
- Body: `{ email, password }`
- Returns: `{ token, user: { uid, email } }`

### POST `/api/auth/login`
Login and receive token.
- Body: `{ email, password }`
- Returns: `{ token, user: { uid, email } }`

### POST `/api/upload`
Upload an image and optionally a prompt; creates a session for authenticated users or guests (with id).
- Form-Data: `image` (file), `prompt` (string, optional)
- Headers:
  - `Authorization: Bearer <token>` OR
  - `X-Guest-Id: <uuid>`
- Returns: `{ sessionId, imageUrl, thumbnail, initialResponse?, overlays }`

### POST `/api/chat`
Send a chat message in a session.
- Body: `{ sessionId, message, imageUrl? }`
- Auth: Optional; guests allowed. If authenticated, session ownership is verified.
- Returns: `{ message, overlays }`

### GET `/api/chat/{session_id}`
Fetch chat history for a session.
- Auth: Optional; authenticated requests validate session ownership.
- Returns: `{ messages: [{ id, from, text, timestamp }, ...] }`

### GET `/api/sessions`
List sessions for the current user.
- Auth: Required (`Authorization` or guest with id stored as `userId`).
- Returns: `{ sessions: [{ sessionId, thumbnail, initialPrompt, createdAt, updatedAt, messageCount }, ...] }`

### GET `/api/sessions/{session_id}/image`
Fetch full image and overlays for a session.
- Auth: Optional; authenticated requests validate session ownership.
- Returns: `{ imageUrl, overlays }`

### POST `/api/sessions`
Create a new session from an image URL and prompt.
- Auth: Required.
- Body: `{ imageUrl, initialPrompt }` (`imageUrl` may be a data URL)
- Returns: `{ sessionId, imageUrl, thumbnail, initialResponse }`

### DELETE `/api/sessions/{session_id}`
Delete a session and its messages/image.
- Auth: Required.
- Returns: `{ success: true, message: 'Session deleted' }`
