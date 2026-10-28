import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@mesterx.io', password: 'admin123' },
  { label: 'PM · Priya', email: 'pm.jane@mesterx.io', password: 'pm123' },
  { label: 'PM · Rajesh', email: 'pm.raj@mesterx.io', password: 'pm123' },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email || 'admin@mesterx.io', password || 'admin123');
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-mark large">MX</span>
          <h1>MesterX Dashboard</h1>
          <p className="subtle">LLM token usage, cost, and savings — at a glance.</p>
        </div>

        <form onSubmit={submit}>
          <label className="field">
            <span className="field-label">Email</span>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@mesterx.io" autoComplete="username" />
          </label>
          <label className="field">
            <span className="field-label">Password</span>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" />
          </label>

          {error && <div className="error-banner"><span className="error-msg">{error}</span></div>}

          <button className="btn btn-primary btn-lg btn-block" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="demo-box">
          <div className="demo-title">Demo accounts</div>
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.email}
              className="demo-account"
              onClick={() => {
                setEmail(a.email);
                setPassword(a.password);
              }}
            >
              <span className="demo-label">{a.label}</span>
              <span className="demo-email mono">{a.email}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}