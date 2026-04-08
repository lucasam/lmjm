import { useState, useRef, useEffect } from 'react';
import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthProvider';
import ProtectedRoute from './auth/ProtectedRoute';
import LoginView from './views/LoginView';
import SpeciesSelectionView from './views/SpeciesSelectionView';
import AnimalListView from './views/cattle/AnimalListView';
import AnimalDetailView from './views/cattle/AnimalDetailView';
import PigDashboard from './views/pigs/PigDashboard';
import ModuleDetailView from './views/pigs/ModuleDetailView';
import BatchDetailView from './views/pigs/BatchDetailView';
import MedicationShotMonthlyView from './views/pigs/MedicationShotMonthlyView';
import MortalityWeeklyView from './views/pigs/MortalityWeeklyView';
import FeedConsumptionDataView from './views/pigs/FeedConsumptionDataView';
import FeedBalanceForecastView from './views/pigs/FeedBalanceForecastView';
import FeedScheduleFullView from './views/pigs/FeedScheduleFullView';
import FiscalDocumentListView from './views/pigs/FiscalDocumentListView';

function NotFound() {
  return (
    <div>
      <h1>Page not found</h1>
      <a href="/">Back to home</a>
    </div>
  );
}

function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const { handleCallback } = useAuth();
  const code = searchParams.get('code');
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    if (!code || calledRef.current) return;
    calledRef.current = true;

    handleCallback(code)
      .then(() => {
        window.location.href = '/';
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Login failed');
      });
  }, [code, handleCallback]);

  if (error) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>{error}</p>
        <a href="/login">Try again</a>
      </div>
    );
  }

  if (!code) {
    return <Navigate to="/login" replace />;
  }

  return <div style={{ padding: '2rem', textAlign: 'center' }}>Processing login...</div>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginView />} />
      <Route path="/callback" element={<OAuthCallback />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <SpeciesSelectionView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cattle"
        element={
          <ProtectedRoute>
            <AnimalListView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/cattle/:earTag"
        element={
          <ProtectedRoute>
            <AnimalDetailView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs"
        element={
          <ProtectedRoute>
            <PigDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/modules/:moduleId"
        element={
          <ProtectedRoute>
            <ModuleDetailView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId"
        element={
          <ProtectedRoute>
            <BatchDetailView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId/medication-shots"
        element={
          <ProtectedRoute>
            <MedicationShotMonthlyView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId/mortality-weekly"
        element={
          <ProtectedRoute>
            <MortalityWeeklyView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId/feed-consumption"
        element={
          <ProtectedRoute>
            <FeedConsumptionDataView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId/feed-forecast"
        element={
          <ProtectedRoute>
            <FeedBalanceForecastView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/batches/:batchId/feed-schedule"
        element={
          <ProtectedRoute>
            <FeedScheduleFullView />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pigs/fiscal-documents"
        element={
          <ProtectedRoute>
            <FiscalDocumentListView />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
