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

  if (code) {
    handleCallback(code).then(() => {
      const from = (window.history.state?.usr?.from as string) || '/';
      window.location.href = from;
    });
    return <div>Processing login...</div>;
  }

  return <Navigate to="/login" replace />;
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
