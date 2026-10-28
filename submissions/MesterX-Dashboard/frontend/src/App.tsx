import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { RequireAuth, RequireRole } from './components/Guards';
import { LoginPage } from './pages/LoginPage';
import { AdminOverviewPage } from './pages/AdminOverviewPage';
import { ProjectPage } from './pages/ProjectPage';
import { DeveloperPage, MyUsagePage } from './pages/DeveloperPage';
import { ModelsPage } from './pages/ModelsPage';
import { UsersPage } from './pages/UsersPage';
import { AdminProjectsPage } from './pages/AdminProjectsPage';
import { AuditPage } from './pages/AuditPage';
import { useAuth } from './context/AuthContext';

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'ADMIN') return <Navigate to="/admin" replace />;
  if (user.role === 'PROJECT_MANAGER' && user.projects.length > 0) return <Navigate to={`/projects/${user.projects[0].id}`} replace />;
  return <Navigate to="/me" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<HomeRedirect />} />
          <Route path="/admin" element={<RequireRole role="ADMIN"><AdminOverviewPage /></RequireRole>} />
          <Route path="/admin/models" element={<RequireRole role="ADMIN"><ModelsPage /></RequireRole>} />
          <Route path="/admin/users" element={<RequireRole role="ADMIN"><UsersPage /></RequireRole>} />
          <Route path="/admin/projects" element={<RequireRole role="ADMIN"><AdminProjectsPage /></RequireRole>} />
          <Route path="/admin/audit" element={<RequireRole role="ADMIN"><AuditPage /></RequireRole>} />
          <Route path="/projects/:id" element={<ProjectPage />} />
          <Route path="/projects/:id/members/:userId" element={<DeveloperPage />} />
          <Route path="/me" element={<MyUsagePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}