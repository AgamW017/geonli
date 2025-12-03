import { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('geonli_token');
    const uid = localStorage.getItem('geonli_uid');
    const email = localStorage.getItem('geonli_email');
    if (token && uid) {
      api.setToken(token);
      setUser({ uid, email });
    }
    setLoading(false);
  }, []);

  const signup = async (email, password) => {
    try {
      setError(null);
      const { data } = await api.client.post('/api/auth/signup', { email, password });
      localStorage.setItem('geonli_token', data.token);
      localStorage.setItem('geonli_uid', data.user.uid);
      localStorage.setItem('geonli_email', data.user.email);
      api.setToken(data.token);
      const u = { uid: data.user.uid, email: data.user.email };
      setUser(u);
      return u;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const login = async (email, password) => {
    try {
      setError(null);
      const { data } = await api.client.post('/api/auth/login', { email, password });
      localStorage.setItem('geonli_token', data.token);
      localStorage.setItem('geonli_uid', data.user.uid);
      localStorage.setItem('geonli_email', data.user.email);
      api.setToken(data.token);
      const u = { uid: data.user.uid, email: data.user.email };
      setUser(u);
      return u;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = async () => {
    try {
      setError(null);
      localStorage.removeItem('geonli_token');
      localStorage.removeItem('geonli_uid');
      localStorage.removeItem('geonli_email');
      api.clearToken();
      setUser(null);
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const getToken = async () => {
    return localStorage.getItem('geonli_token');
  };

  const value = {
    user,
    loading,
    error,
    signup,
    login,
    logout,
    getToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
