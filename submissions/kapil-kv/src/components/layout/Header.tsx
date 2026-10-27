"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";

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
    <header className="flex h-14 items-center justify-between border-b border-[var(--border)] bg-[var(--background)] px-4">
      <div className="flex items-center gap-4 lg:hidden">
        <span className="text-lg font-bold text-[var(--primary)]">SLA Tracker</span>
      </div>
      <div className="hidden lg:block" />
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={handleLogout} loading={loggingOut}>
          Logout
        </Button>
      </div>
    </header>
  );
}