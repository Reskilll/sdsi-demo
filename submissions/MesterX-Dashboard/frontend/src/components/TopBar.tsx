import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Sun, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { rangeFor, type PresetKey, type DateRange } from '../lib/dateRange';
import clsx from 'clsx';

const PRESETS: { key: PresetKey; label: string }[] = [
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: '90d', label: 'Last 90 days' },
  { key: 'month', label: 'This month' },
];

export interface TopBarFilters {
  range: DateRange;
  projectId: number | 'all';
}

interface Props {
  showProjectSwitcher?: boolean;
  filters?: TopBarFilters;
  onFiltersChange?: (f: TopBarFilters) => void;
}

export function TopBar({ showProjectSwitcher, filters, onFiltersChange }: Props) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [preset, setPreset] = useState<PresetKey | 'custom'>('30d');

  const handlePreset = (key: PresetKey) => {
    setPreset(key);
    if (onFiltersChange && filters) onFiltersChange({ ...filters, range: rangeFor(key) });
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        {showProjectSwitcher && user?.role === 'ADMIN' && onFiltersChange && filters && (
          <select
            className="select project-switcher"
            value={filters.projectId}
            onChange={(e) => onFiltersChange({ ...filters, projectId: e.target.value === 'all' ? 'all' : Number(e.target.value) })}
          >
            <option value="all">Organisation-level</option>
            {user.projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="topbar-right">
        {onFiltersChange && filters && (
          <div className="range-presets">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                className={clsx('preset-btn', preset === p.key && 'preset-active')}
                onClick={() => handlePreset(p.key)}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        <button className="icon-btn" onClick={toggle} aria-label="Toggle theme" title="Toggle theme">
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
        </button>

        <div className="user-menu">
          <button className="user-menu-btn">
            <span className="avatar">{user?.displayName?.charAt(0) ?? 'U'}</span>
            <span className="user-name">{user?.displayName ?? 'User'}</span>
            <ChevronDown size={14} />
          </button>
          <div className="user-menu-dropdown">
            <div className="user-menu-info">
              <div className="user-menu-email">{user?.email}</div>
            </div>
            <button className="user-menu-item" onClick={handleLogout}>
              <LogOut size={15} /> Sign out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}