import axios from 'axios';
import { auth } from '../config/firebase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});
apiClient.interceptors.request.use(
  async (config) => {
    const user = auth.currentUser;
    if (user) {
      const token = await user.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      console.error('Authentication error');
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  uploadImage: async (imageFile, prompt = '') => {
    const formData = new FormData();
    formData.append('image', imageFile);
    if (prompt) formData.append('prompt', prompt);

    const response = await apiClient.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  // Send chat message
  sendMessage: async (sessionId, message, imageUrl = null) => {
    const response = await apiClient.post('/api/chat', {
      sessionId,
      message,
      imageUrl,
    });
    return response.data;
  },

  // Get chat history (messages only, loaded separately)
  getChatHistory: async (sessionId) => {
    const response = await apiClient.get(`/api/chat/${sessionId}`);
    return response.data;
  },

  // Get user sessions (lightweight - only thumbnails, no full images)
  getSessions: async () => {
    const response = await apiClient.get('/api/sessions');
    return response.data;
  },

  // Get full image and overlays for a specific session (loaded on demand)
  getSessionImage: async (sessionId) => {
    const response = await apiClient.get(`/api/sessions/${sessionId}/image`);
    return response.data;
  },

  // Create new session
  createSession: async (imageUrl, initialPrompt) => {
    const response = await apiClient.post('/api/sessions', {
      imageUrl,
      initialPrompt,
    });
    return response.data;
  },

  // Delete session
  deleteSession: async (sessionId) => {
    const response = await apiClient.delete(`/api/sessions/${sessionId}`);
    return response.data;
  },
};

export default apiClient;
