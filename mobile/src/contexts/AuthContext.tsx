import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { calendarAPI } from '../services/api';

interface User {
  name: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshAuth = async () => {
    try {
      setIsLoading(true);
      
      // Check if we have stored tokens
      const { accessToken, refreshToken } = await calendarAPI.getStoredTokens();
      
      if (!accessToken || !refreshToken) {
        // No tokens stored, user is not authenticated
        setUser(null);
        return;
      }
      
      // Try to get current user to validate the token
      try {
        const currentUser = await calendarAPI.getCurrentUser();
        setUser(currentUser);
      } catch (error) {
        console.error('Token validation failed:', error);
        // Token is invalid, clear user state and tokens
        setUser(null);
        await calendarAPI.logout();
      }
    } catch (error) {
      console.error('Error refreshing auth:', error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshAuth();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await calendarAPI.login({ email, password });
      // Use user data from login response instead of making another API call
      setUser({
        name: response.user_name,
      });
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await calendarAPI.register({ name, email, password });
      // Use user data from register response instead of making another API call
      setUser({
        name: response.user_name,
      });
    } catch (error) {
      console.error('Register error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      await calendarAPI.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      // Clear user state even if logout fails
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 