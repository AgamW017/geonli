# GeoNLI Frontend

Vite + React SPA for uploading images, chatting with mock AI responses, and viewing overlays. Integrates with the GeoNLI backend and supports JWT or persistent guest mode.

## Tech Stack
- React 18, Vite
- Axios
- Tailwind CSS
- React Transition Group
- react-zoom-pan-pinch

## File Structure
```
frontend/
  index.html
  package.json
  postcss.config.js
  tailwind.config.js
  vite.config.js
  src/
    main.jsx
    App.jsx
    index.css
    contexts/
      AuthContext.jsx
      ThemeContext.jsx
    pages/
      ChatPage.jsx
      LoginPage.jsx
      UploadPage.jsx
    components/
      Topbar.jsx
      LeftSidebar.jsx
      ChatPanel.jsx
      ImageViewer.jsx
      icons/
        Icon.jsx
        index.js
        MenuIcon.jsx
        MessageSquareIcon.jsx
        PlusIcon.jsx
        SendIcon.jsx
        UploadCloudIcon.jsx
    services/
      api.js
```

## Scripts
```
npm run dev       # Start dev server (port 3000)
npm run build     # Production build
npm run preview   # Preview built assets
npm run lint      # Lint source
```

## Dev Server
- Port: `3000`

## Styling
- Tailwind configured in `tailwind.config.js` and `postcss.config.js`

## Environment Variables
- `VITE_API_URL` (optional): Backend base URL; default `http://localhost:8000`
  - Place in `frontend/.env`: `VITE_API_URL=http://localhost:8000`

## Auth & Guest Mode
- If `geonli_token` exists in `localStorage`, requests include `Authorization: Bearer <token>`.
- Otherwise, a persistent `geonli_guest_id` is generated and sent via `X-Guest-Id` header.

## Backend Integration (`src/services/api.js`)
- `uploadImage(imageFile, prompt?)`: POST `/api/upload` (multipart)
- `sendMessage(sessionId, message, imageUrl?)`: POST `/api/chat`
- `getChatHistory(sessionId)`: GET `/api/chat/{sessionId}`
- `getSessions()`: GET `/api/sessions`
- `getSessionImage(sessionId)`: GET `/api/sessions/{sessionId}/image`
- `createSession(imageUrl, initialPrompt)`: POST `/api/sessions`
- `deleteSession(sessionId)`: DELETE `/api/sessions/{sessionId}`

## Quick Start
```
# From frontend/
npm install
npm run dev
```
UI runs on `http://localhost:3000`.

## Build & Preview
```
npm run build
npm run preview
```

## Linting
```
npm run lint
```

