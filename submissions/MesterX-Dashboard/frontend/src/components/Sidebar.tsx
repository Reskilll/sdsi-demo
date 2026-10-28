import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import { LayoutDashboard, FolderKanban, Boxes, Users, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
}

const NAV: NavItem[] = [
  { to: '/admin', label: 'Overview', icon: <LayoutDashboard size={18} />, adminOnly: true },
  { to: '/admin/projects', label: 'Projects', icon: <FolderKanban size={18} />, adminOnly: true },
  { to: '/admin/models', label: 'Models', icon: <Boxes size={18} />, adminOnly: true },
  { to: '/admin/users', label: 'Users', icon: <Users size={18} />, adminOnly: true },
  { to: '/admin/audit', label: 'Audit log', icon: <Shield size={18} />, adminOnly: true },
];

export function Sidebar() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">MX</span>
        <span className="brand-name">MesterX</span>
      </div>

      {isAdmin ? (
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/admin'}
              className={({ isActive }) => clsx('nav-item', isActive && 'nav-active')}
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      ) : (
        <nav className="nav">
          {user?.projects.map((p) => (
            <NavLink key={p.id} to={`/projects/${p.id}`} className={({ isActive }) => clsx('nav-item', isActive && 'nav-active')}>
              <FolderKanban size={18} />
              <span>{p.name}</span>
            </NavLink>
          ))}
          <NavLink to="/me" className={({ isActive }) => clsx('nav-item', isActive && 'nav-active')}>
            <Users size={18} />
            <span>My usage</span>
          </NavLink>
        </nav>
      )}

      <div className="sidebar-foot">
        <div className="sidebar-version">MesterX Dashboard · v0.1</div>
      </div>
    </aside>
  );
}