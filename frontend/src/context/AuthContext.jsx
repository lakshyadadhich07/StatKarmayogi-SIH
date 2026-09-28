import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setToken, clearToken, getToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('sk_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(!!getToken()); // loading only if token exists

  // Validate persisted token on mount
  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api.auth.me()
      .then((me) => {
        setUser(me);
        localStorage.setItem('sk_user', JSON.stringify(me));
      })
      .catch(() => {
        clearToken();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  // Listen for 401 events from the API client
  useEffect(() => {
    const handler = () => {
      setUser(null);
      navigate('/login', { replace: true });
    };
    window.addEventListener('auth:expired', handler);
    return () => window.removeEventListener('auth:expired', handler);
  }, [navigate]);

  const login = useCallback(async (email, password) => {
    const data = await api.auth.login(email, password);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('sk_user', JSON.stringify(data.user));
    return data.user;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    localStorage.removeItem('sk_user');
    navigate('/login', { replace: true });
  }, [navigate]);

  const register = useCallback(async (payload) => {
    return api.auth.register(payload);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
