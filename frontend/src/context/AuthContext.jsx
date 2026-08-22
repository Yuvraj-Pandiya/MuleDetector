import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('mule-auth-user');
    return stored ? JSON.parse(stored) : null;
  });

  useEffect(() => {
    if (user) {
      localStorage.setItem('mule-auth-user', JSON.stringify(user));
    } else {
      localStorage.removeItem('mule-auth-user');
    }
  }, [user]);

  const login = (email, password) => {
    // Simulated login — replace with real API call
    const userData = {
      name: email.split('@')[0],
      email,
      role: 'Analyst',
      loginTime: new Date().toISOString(),
    };
    setUser(userData);
    return userData;
  };

  const signup = (name, email, password) => {
    // Simulated signup — replace with real API call
    const userData = {
      name,
      email,
      role: 'Analyst',
      loginTime: new Date().toISOString(),
    };
    setUser(userData);
    return userData;
  };

  const logout = () => {
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
