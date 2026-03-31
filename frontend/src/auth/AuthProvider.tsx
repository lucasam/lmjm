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
  loading: boolean;
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
  const [loading, setLoading] = useState(true);

  // On mount: check tokens, try refresh if expired
  useEffect(() => {
    async function init() {
      const idToken = getStoredIdToken();
      const accessToken = getStoredAccessToken();

      // Case 1: valid tokens exist
      if (accessToken && !isTokenExpired(accessToken) && idToken) {
        const parsed = parseUserFromIdToken(idToken);
        if (parsed) {
          setUser(parsed);
          setIsAuthenticated(true);
          setLoading(false);
          return;
        }
      }

      // Case 2: tokens expired but refresh token exists — try refresh
      const refreshTokenStored = localStorage.getItem('lmjm_refresh_token');
      if (refreshTokenStored) {
        const newToken = await cognitoRefreshToken();
        if (newToken) {
          const freshIdToken = getStoredIdToken();
          if (freshIdToken) {
            const parsed = parseUserFromIdToken(freshIdToken);
            if (parsed) {
              setUser(parsed);
              setIsAuthenticated(true);
              setLoading(false);
              return;
            }
          }
        }
      }

      // Case 3: no valid tokens, not refreshable
      setIsAuthenticated(false);
      setLoading(false);
    }

    init();
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

    const newToken = await cognitoRefreshToken();
    if (newToken) {
      const idToken = getStoredIdToken();
      if (idToken) {
        const parsed = parseUserFromIdToken(idToken);
        if (parsed) setUser(parsed);
      }
      return newToken;
    }

    cognitoLogout();
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/login';
    throw new Error('Session expired');
  }, []);

  const value: AuthContextValue = {
    isAuthenticated,
    loading,
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
