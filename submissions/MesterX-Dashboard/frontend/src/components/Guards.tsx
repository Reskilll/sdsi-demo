import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Skeleton } from '../components/Skeleton';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="page page-center">
        <Skeleton h={24} w={240} />
        <Skeleton h={16} w={160} style={{ marginTop: 8 }} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

export function RequireRole({ role, children }: { role: 'ADMIN' | 'PROJECT_MANAGER' | 'DEVELOPER'; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return null;

  if (role === 'ADMIN' && user.role !== 'ADMIN') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}