import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'researcher' | 'advocate';
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    // Demo login - in production, this would call your backend
    const demoUsers = {
      'admin@kenyalaw.ai': { id: '1', name: 'Admin User', email: 'admin@kenyalaw.ai', role: 'admin' as const },
      'researcher@kenyalaw.ai': { id: '2', name: 'Legal Researcher', email: 'researcher@kenyalaw.ai', role: 'researcher' as const },
      'advocate@kenyalaw.ai': { id: '3', name: 'Advocate', email: 'advocate@kenyalaw.ai', role: 'advocate' as const },
      // Keep old emails for backward compatibility
      'admin@patriotai.ke': { id: '1', name: 'Admin User', email: 'admin@patriotai.ke', role: 'admin' as const },
      'analyst@patriotai.ke': { id: '2', name: 'Legal Researcher', email: 'analyst@patriotai.ke', role: 'researcher' as const }
    };

    if (demoUsers[email as keyof typeof demoUsers] && password === 'demo123') {
      const userData = demoUsers[email as keyof typeof demoUsers];
      setUser(userData);
      localStorage.setItem('user', JSON.stringify(userData));
    } else {
      throw new Error('Invalid credentials');
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  const value = {
    user,
    login,
    logout,
    isLoading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
