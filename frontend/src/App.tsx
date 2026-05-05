import { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@chakra-ui/react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSpinner from './components/LoadingSpinner';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Chat from './pages/Chat';
import Organizations from './pages/Organizations';
import CreateOrganization from './pages/CreateOrganization';
import OrganizationDetail from './pages/OrganizationDetail';
import Admin from './pages/Admin';
import ResetPassword from './pages/ResetPassword';
import NotFound from './pages/NotFound';

const PrivateRoute = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner fullScreen message="Loading..." />;
  }

  return isAuthenticated ? children : <Navigate to="/" />;
};

const Layout = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated } = useAuth();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  if (!isAuthenticated) {
    return children;
  }

  const sidebarWidth = isSidebarCollapsed ? '64px' : '260px';

  return (
    <Box display="flex" h="100vh" bg="surface.950">
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />
      <Box
        flex="1"
        ml={sidebarWidth}
        overflowY="auto"
        transition="margin-left 0.2s ease"
      >
        {children}
      </Box>
    </Box>
  );
};

const AppRoutes = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to="/chat" /> : <Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/chat"
        element={
          <PrivateRoute>
            <Layout>
              <Chat />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/organizations"
        element={
          <PrivateRoute>
            <Layout>
              <Organizations />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/organizations/new"
        element={
          <PrivateRoute>
            <Layout>
              <CreateOrganization />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/organizations/:id"
        element={
          <PrivateRoute>
            <Layout>
              <OrganizationDetail />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <PrivateRoute>
            <Layout>
              <Admin />
            </Layout>
          </PrivateRoute>
        }
      />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
