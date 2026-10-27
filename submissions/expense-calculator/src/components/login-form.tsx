/**
 * Login / Register form with validation, error states, and demo account cards.
 */

'use client';

import { useCallback, useState } from 'react';
import { LogIn, UserPlus, Mail, Lock, User, Eye, EyeOff, ArrowRight, Users, Copy, Check, LogInIcon } from 'lucide-react';
import { login, register } from '@/lib/auth';
import { seedTestUsers } from '@/lib/seed-users';

interface LoginFormProps {
  onSuccess: () => void;
}

type Mode = 'login' | 'register';

const DEMO_ACCOUNTS = [
  { name: 'Alice Johnson', email: 'alice@demo.com',  avatar: 'AJ' },
  { name: 'Bob Smith',     email: 'bob@demo.com',    avatar: 'BS' },
  { name: 'Charlie Park',  email: 'charlie@demo.com', avatar: 'CP' },
  { name: 'Diana Lee',     email: 'diana@demo.com',  avatar: 'DL' },
  { name: 'Eve Chen',      email: 'eve@demo.com',    avatar: 'EC' },
] as const;

const DEMO_PASSWORD = 'demo123';

export default function LoginForm({ onSuccess }: LoginFormProps) {
  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [activeAccount, setActiveAccount] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // ---- Prefill a demo account ----
  const prefillAccount = useCallback((accountEmail: string) => {
    setMode('login');
    setEmail(accountEmail);
    setPassword(DEMO_PASSWORD);
    setActiveAccount(accountEmail);
    setErrors({});
  }, []);

  // ---- Seed + prefill first account ----
  const handleSeedAndFill = useCallback(() => {
    seedTestUsers();
    setSeeded(true);
    prefillAccount(DEMO_ACCOUNTS[0].email);
  }, [prefillAccount]);

  // ---- Copy credentials ----
  const handleCopyCreds = useCallback(async () => {
    const text = DEMO_ACCOUNTS.map(a => `${a.email} / ${DEMO_PASSWORD}`).join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      // Client-side quick check
      const newErrors: Record<string, string> = {};
      if (mode === 'register' && (!name.trim() || name.trim().length < 2)) {
        newErrors.name = 'Name must be at least 2 characters.';
      }
      if (!email.trim()) {
        newErrors.email = 'Please enter your email.';
      }
      if (!password) {
        newErrors.password = 'Password is required.';
      }
      if (mode === 'register' && password !== confirmPassword) {
        newErrors.confirmPassword = 'Passwords do not match.';
      }
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return;
      }

      setLoading(true);
      setErrors({});
      try {
        const result =
          mode === 'login'
            ? login({ email: email.trim(), password })
            : register({ name: name.trim(), email: email.trim(), password });

        if (result.success) {
          onSuccess();
        } else {
          setErrors({ form: result.error ?? 'Authentication failed.' });
        }
      } finally {
        setLoading(false);
      }
    },
    [mode, email, password, name, confirmPassword, onSuccess],
  );

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-surface to-surface-alt">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold tracking-tight">
            Split<span className="text-primary">Sage</span>
          </h1>
          <p className="text-muted mt-2 text-sm">
            Smart expense splitting with minimum settlements
          </p>
        </div>

        {/* Form card */}
        <div className="bg-surface-alt border border-border rounded-2xl p-6 shadow-xl">
          {/* Mode toggle */}
          <div className="flex bg-surface rounded-xl p-1 mb-6">
            <button
              onClick={() => { setMode('login'); setErrors({}); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                mode === 'login'
                  ? 'bg-primary text-white shadow'
                  : 'text-muted hover:text-white'
              }`}
            >
              <LogIn className="w-4 h-4" />
              Login
            </button>
            <button
              onClick={() => { setMode('register'); setErrors({}); }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-4 rounded-lg text-sm font-medium transition-all ${
                mode === 'register'
                  ? 'bg-primary text-white shadow'
                  : 'text-muted hover:text-white'
              }`}
            >
              <UserPlus className="w-4 h-4" />
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium mb-1.5">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className={`w-full bg-surface border ${
                      errors.name ? 'border-danger' : 'border-border'
                    } rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors`}
                    placeholder="John Doe"
                    autoComplete="name"
                  />
                </div>
                {errors.name && (
                  <p className="text-danger text-xs mt-1">{errors.name}</p>
                )}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`w-full bg-surface border ${
                    errors.email ? 'border-danger' : 'border-border'
                  } rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors`}
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
              {errors.email && (
                <p className="text-danger text-xs mt-1">{errors.email}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full bg-surface border ${
                    errors.password ? 'border-danger' : 'border-border'
                  } rounded-xl pl-10 pr-10 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors`}
                  placeholder="••••••••"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-white transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-danger text-xs mt-1">{errors.password}</p>
              )}
            </div>

            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium mb-1.5">Confirm Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={`w-full bg-surface border ${
                      errors.confirmPassword ? 'border-danger' : 'border-border'
                    } rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:border-primary transition-colors`}
                    placeholder="••••••••"
                    autoComplete="new-password"
                  />
                </div>
                {errors.confirmPassword && (
                  <p className="text-danger text-xs mt-1">{errors.confirmPassword}</p>
                )}
              </div>
            )}

            {errors.form && (
              <div className="bg-danger/10 border border-danger/30 rounded-xl px-4 py-2.5">
                <p className="text-danger text-sm text-center">{errors.form}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed py-2.5 rounded-xl font-medium transition-colors text-white"
            >
              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* ---- Demo Accounts Card ---- */}
          <div className="mt-6 pt-5 border-t border-border">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                Demo Accounts
              </p>
              <button
                type="button"
                onClick={handleCopyCreds}
                className="flex items-center gap-1 text-[10px] text-muted hover:text-white transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-success" />
                    <span className="text-success">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy all
                  </>
                )}
              </button>
            </div>

            {/* One-click seed + prefill button */}
            {!seeded && (
              <button
                type="button"
                onClick={handleSeedAndFill}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 mb-3 bg-success/10 border border-success/30 rounded-xl text-sm text-success hover:bg-success/20 transition-colors font-medium"
              >
                <UserPlus className="w-4 h-4" />
                Create demo accounts & fill Alice
              </button>
            )}

            {/* Account list */}
            <div className="space-y-1.5">
              {DEMO_ACCOUNTS.map((account) => {
                const isActive = activeAccount === account.email;
                return (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => prefillAccount(account.email)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-all ${
                      isActive
                        ? 'bg-primary/15 border border-primary/40 ring-1 ring-primary/30'
                        : 'bg-surface hover:bg-surface/70 border border-transparent hover:border-border'
                    }`}
                  >
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                      isActive ? 'bg-primary text-white' : 'bg-surface-alt text-muted'
                    }`}>
                      {account.avatar}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-medium truncate ${isActive ? 'text-white' : ''}`}>
                        {account.name}
                      </p>
                      <p className="text-[11px] text-muted truncate">
                        {account.email}
                      </p>
                    </div>
                    <span className={`shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      isActive ? 'bg-primary/20 text-primary' : 'bg-surface-alt text-muted'
                    }`}>
                      {DEMO_PASSWORD}
                    </span>
                    {isActive && (
                      <LogInIcon className="w-3.5 h-3.5 text-primary shrink-0" />
                    )}
                  </button>
                );
              })}
            </div>

            <p className="text-[10px] text-muted text-center mt-3">
              Click any account to fill login form · All passwords are <code className="text-primary/80">demo123</code>
            </p>
          </div>
        </div>

        {/* Footer note */}
        <p className="text-[10px] text-muted text-center mt-4">
          Passwords are stored locally and never sent anywhere.
        </p>
      </div>
    </div>
  );
}