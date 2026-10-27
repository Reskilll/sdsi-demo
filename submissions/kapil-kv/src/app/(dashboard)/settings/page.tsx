"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export default function SettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionInfo, setSessionInfo] = useState<{ email: string; role: string } | null>(null);

  useEffect(() => {
    fetchSession();
  }, []);

  async function fetchSession() {
    try {
      const res = await fetch("/api/auth/session");
      const json = await res.json();
      if (json.success) {
        setSessionInfo(json.data.admin);
      }
    } catch {
      // silent
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      // Password change endpoint not available (would need admin management API)
      // This is a placeholder for the real implementation
      setMessage("Password change requires direct MongoDB admin update. Use the seed script with new credentials or manage manually.");
    } catch {
      setError("Failed to change password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {sessionInfo && (
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h2 className="mb-2 text-lg font-semibold">Account Info</h2>
          <p className="text-sm">Email: <span className="font-medium">{sessionInfo.email}</span></p>
          <p className="text-sm">Role: <span className="font-medium">{sessionInfo.role}</span></p>
        </div>
      )}

      <div className="rounded-lg border border-[var(--border)] p-4">
        <h2 className="mb-2 text-lg font-semibold">Change Password</h2>
        <p className="mb-4 text-sm text-[var(--muted-foreground)]">
          To change the admin password, update the ADMIN_PASSWORD variable in your .env.local and re-run:
          <br />
          <code className="rounded bg-[var(--muted)] px-1.5 py-0.5 text-xs">npm run seed:admin</code>
        </p>
        <p className="text-sm text-[var(--muted-foreground)]">
          This ensures the password is properly hashed and stored securely.
        </p>
      </div>

      <div className="rounded-lg border border-[var(--border)] p-4">
        <h2 className="mb-2 text-lg font-semibold">Business Configuration</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Business hours and timezone are configured in .env.local:
        </p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-[var(--muted-foreground)]">
          <li>APP_TIMEZONE: Asia/Kolkata</li>
          <li>BUSINESS_START_HOUR: 9 (09:00)</li>
          <li>BUSINESS_END_HOUR: 18 (18:00)</li>
          <li>Working days: Monday–Friday</li>
        </ul>
      </div>
    </div>
  );
}