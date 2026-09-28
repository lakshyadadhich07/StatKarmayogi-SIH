import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Spinner } from './components/ui';

// Screens
import AuthPage from './screens/AuthPage';
import TrainerConsole from './screens/TrainerConsole';
import SMEDashboard from './screens/SMEDashboard';
import OfficerDashboard from './screens/OfficerDashboard';
import AdminDashboard from './screens/AdminDashboard';

/**
 * Higher-order component to protect routes based on authentication and role.
 */
function ProtectedRoute({ allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f4f6f9]">
        <Spinner size="lg" className="text-[#c97d2e]" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // If authenticated but unauthorized, push them to their home dashboard
    const roleRoutes = {
      OFFICER: '/officer',
      TRAINER: '/trainer',
      SME: '/sme',
      ADMIN: '/admin',
    };
    return <Navigate to={roleRoutes[user.role] || '/login'} replace />;
  }

  return <Outlet />;
}

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f4f6f9]">
        <Spinner size="lg" className="text-[#c97d2e]" />
      </div>
    );
  }

  return (
    <Routes>
      {/* Public / Auth */}
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage />} />

      {/* Root redirect based on role */}
      <Route path="/" element={
        !user ? <Navigate to="/login" replace /> :
        user.role === 'OFFICER' ? <Navigate to="/officer" replace /> :
        user.role === 'TRAINER' ? <Navigate to="/trainer" replace /> :
        user.role === 'SME' ? <Navigate to="/sme" replace /> :
        <Navigate to="/admin" replace />
      } />

      {/* Officer Routes */}
      <Route element={<ProtectedRoute allowedRoles={['OFFICER']} />}>
        <Route path="/officer/*" element={<OfficerDashboard />} />
      </Route>

      {/* Trainer Routes */}
      <Route element={<ProtectedRoute allowedRoles={['TRAINER', 'ADMIN']} />}>
        <Route path="/trainer/*" element={<TrainerConsole />} />
      </Route>

      {/* SME Routes */}
      <Route element={<ProtectedRoute allowedRoles={['SME', 'ADMIN']} />}>
        <Route path="/sme/*" element={<SMEDashboard />} />
      </Route>

      {/* Admin Routes */}
      <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
        <Route path="/admin/*" element={<AdminDashboard />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}

export default App;

