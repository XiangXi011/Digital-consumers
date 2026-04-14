import { Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { setOnUnauthorized } from './lib/api';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './components/LoginPage';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastContainer } from './components/Toast';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import PersonaLibrary from './pages/PersonaLibrary';
import Report from './pages/Report';
import NewProject from './pages/NewProject';
import ProjectDetail from './pages/ProjectDetail';
import Docs from './pages/Docs';
import Settings from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

function AppRoutes() {
  const navigate = useNavigate();

  // When api.js detects a 401 that can't be refreshed, redirect to login
  useEffect(() => {
    setOnUnauthorized(() => navigate('/login', { replace: true }));
    return () => setOnUnauthorized(null);
  }, [navigate]);

  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/new" element={<NewProject />} />
                  <Route path="/projects/:id" element={<ProjectDetail />} />
                  <Route path="/personas" element={<PersonaLibrary />} />
                  <Route path="/reports" element={<Report />} />
                  <Route path="/docs" element={<Docs />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastContainer />
        <AppRoutes />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
