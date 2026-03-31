import { useAuth } from './AuthProvider';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, loading, login } = useAuth();

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;
  }

  if (!isAuthenticated) {
    login();
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Redirecting to login...</div>;
  }

  return <>{children}</>;
}
