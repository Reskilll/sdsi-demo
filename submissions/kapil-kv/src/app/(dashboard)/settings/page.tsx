"use client";

import { useState, useEffect } from "react";

interface SessionData {
  email: string;
  role: string;
}

export default function SettingsPage() {
  const [sessionInfo, setSessionInfo] = useState<SessionData | null>(null);

  useEffect(() => {
    async function fetchSession() {
      try {
        const res = await fetch("/api/auth/session");
        const json = await res.json();
        if (json.success) setSessionInfo(json.data.admin);
      } catch { /* silent */ }
    }
    fetchSession();
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Settings</h1>
        <p className="mt-0.5 text-sm text-slate-500">Manage your account and application configuration</p>
      </div>

      {/* Account Info */}
      {sessionInfo && (
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">Account Information</h2>
              <p className="text-xs text-slate-500">Currently signed in</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2.5 text-sm">
              <span className="text-slate-500">Email</span>
              <span className="font-medium text-slate-900">{sessionInfo.email}</span>
            </div>
            <div className="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-2.5 text-sm">
              <span className="text-slate-500">Role</span>
              <span className="font-medium text-slate-900">{sessionInfo.role}</span>
            </div>
          </div>
        </div>
      )}

      {/* Change Password */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">Change Password</h2>
            <p className="text-xs text-slate-500">Update your admin credentials</p>
          </div>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm text-amber-800">
            Update <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium">ADMIN_PASSWORD</code> in
            your <code className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium">.env.local</code> file, then run:
          </p>
          <pre className="mt-2 select-all rounded-lg bg-amber-100/50 px-3 py-2 text-xs font-mono text-amber-900">
            npm run seed:admin
          </pre>
          <p className="mt-2 text-xs text-amber-700">
            The password will be hashed and stored securely in MongoDB.
          </p>
        </div>
      </div>

      {/* Business Configuration */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-50 text-sky-600">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-700">Business Configuration</h2>
            <p className="text-xs text-slate-500">Working hours and timezone settings</p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { label: "Timezone", value: "Asia/Kolkata" },
            { label: "Business Hours", value: "09:00 – 18:00" },
            { label: "Working Days", value: "Monday – Friday" },
            { label: "Configuration File", value: ".env.local" },
          ].map((item) => (
            <div key={item.label} className="rounded-lg bg-slate-50 px-4 py-2.5 text-sm">
              <span className="text-slate-500">{item.label}</span>
              <p className="mt-0.5 font-medium text-slate-900">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}