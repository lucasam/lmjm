import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  login as cognitoLogin,
  handleCallback as cognitoHandleCallback,
  refreshToken as cognitoRefreshToken,
  logout as cognitoLogout,
  getStoredAccessToken,
  getStoredIdToken,
  decodeJwtPayload,
  isTokenExpired,
} from './cognito';

interface AuthUser {
  name: string;
  email: string;
}

interface AuthContextValue {
  isAuthenticated: boolean;
  user: AuthUser | null;
  login(): void;
  handleCallback(code: string): Promise<void>;
  logout(): void;
  getAccessToken(): Promise<string>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function parseUserFromIdToken(idToken: string): AuthUser | null {
  try {
    const payload = decodeJwtPayload(idToken);
    return {
      name: (payload.name as string) ?? (payload.email as string) ?? '',
      email: (payload.email as string) ?? '',
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // On mount: check if tokens exist and parse user
  useEffect(() => {
    const idToken = getStoredIdToken();
    const accessToken = getStoredAccessToken();
    if (idToken && accessToken) {
      const parsed = parseUserFromIdToken(idToken);
      if (parsed) {
        setUser(parsed);
        setIsAuthenticated(true);
      }
    }
  }, []);

  const login = useCallback(() => {
    cognitoLogin();
  }, []);

  const handleCallback = useCallback(async (code: string) => {
    const tokens = await cognitoHandleCallback(code);
    const parsed = parseUserFromIdToken(tokens.id_token);
    setUser(parsed);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    cognitoLogout();
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/login';
  }, []);

  const getAccessToken = useCallback(async (): Promise<string> => {
    const token = getStoredAccessToken();
    if (token && !isTokenExpired(token)) {
      return token;
    }

    // Token expired or missing — attempt refresh
    const newToken = await cognitoRefreshToken();
    if (newToken) {
      // Also update user from refreshed id token
      const idToken = getStoredIdToken();
      if (idToken) {
        const parsed = parseUserFromIdToken(idToken);
        if (parsed) setUser(parsed);
      }
      return newToken;
    }

    // Refresh failed — clear tokens and redirect to login
    cognitoLogout();
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/login';
    throw new Error('Session expired');
  }, []);

  const value: AuthContextValue = {
    isAuthenticated,
    user,
    login,
    handleCallback,
    logout,
    getAccessToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
