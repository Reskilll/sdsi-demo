"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/utils/cn";

function IconLogout() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
      <path fill="currentColor" className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function Header() {
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      const res = await fetch("/api/auth/logout", { method: "POST" });
      if (res.ok) {
        router.push("/login");
        router.refresh();
      }
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      {/* Mobile brand */}
      <div className="flex items-center gap-3 lg:hidden">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
          </svg>
        </div>
        <span className="text-lg font-bold text-slate-900">SLA Tracker</span>
      </div>

      {/* Spacer */}
      <div className="hidden lg:block" />

      {/* Right section */}
      <div className="flex items-center gap-4">
        <div className="hidden items-center gap-2 text-sm font-medium text-slate-500 sm:flex">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-slate-500">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <span>Admin</span>
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-sm font-medium text-slate-700",
            "transition-colors hover:bg-slate-50 active:bg-slate-100",
            "focus:outline-none focus:ring-2 focus:ring-indigo-500/20",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        >
          {loggingOut ? <Spinner /> : <IconLogout />}
          Logout
        </button>
      </div>
    </header>
  );
}