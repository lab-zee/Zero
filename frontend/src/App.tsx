import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@chakra-ui/react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SidebarProvider, useSidebar } from './contexts/SidebarContext';
import ChatSidebar from './components/ChatSidebar';
import AppMenuButton from './components/AppMenuButton';
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

const AuthenticatedShell = ({ children }: { children: React.ReactElement }) => {
  const { isOpen, closeSidebar } = useSidebar();

  return (
    <Box display="flex" h="100vh" bg="surface.950">
      <AppMenuButton />
      <ChatSidebar isOpen={isOpen} onClose={closeSidebar} />
      {/* overflowY auto so pages like Admin can scroll; Chat manages its own inner scroll */}
      <Box flex="1" minW={0} h="100vh" overflowY="auto" overflowX="hidden">
        {children}
      </Box>
    </Box>
  );
};

const Layout = ({ children }: { children: React.ReactElement }) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return children;
  }

  return (
    <SidebarProvider>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </SidebarProvider>
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
