"use client";

import { useEffect, useState } from "react";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { formatDuration } from "@/utils/formatters";

interface DashboardData {
  summary: {
    total: number;
    open: number;
    inProgress: number;
    onHold: number;
    resolved: number;
    breached: number;
    onTrack: number;
    atRisk: number;
    slaCompliance: number;
    avgResolutionTime: number;
    avgBreachDuration: number;
  };
  breachesByPriority: Array<{
    priority: string;
    total: number;
    breached: number;
    percentage: number;
  }>;
  breachesByGroup: Array<{
    name: string;
    total: number;
    breached: number;
    percentage: number;
  }>;
  statusDistribution: Record<string, number>;
}

const priorityBadgeVariant: Record<string, "danger" | "warning" | "info" | "default"> = {
  P1: "danger",
  P2: "warning",
  P3: "info",
  P4: "default",
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboard();
  }, []);

  async function fetchDashboard() {
    try {
      const res = await fetch("/api/dashboard/summary");
      const json = await res.json();
      if (json.success) {
        setData(json.data);
      } else {
        setError(json.error?.message || "Failed to load dashboard.");
      }
    } catch {
      setError("Unable to connect to server.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
        <p className="mt-3 text-sm text-slate-500">Loading dashboard...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-red-50">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-500">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="text-sm font-medium text-red-700">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { summary, breachesByPriority, breachesByGroup, statusDistribution } = data;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            SLA compliance overview for your service desk
          </p>
        </div>
        <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="text-sm text-slate-500">Live</span>
        </div>
      </div>

      {/* KPI Row 1 */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Key Metrics
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-7">
          <StatCard label="Total Tickets" value={summary.total} variant="default" />
          <StatCard label="Open" value={summary.open} variant="info" />
          <StatCard label="On Hold" value={summary.onHold} variant="warning" />
          <StatCard label="Resolved" value={summary.resolved} variant="success" />
          <StatCard label="Breached" value={summary.breached} variant="danger" />
          <StatCard label="On Track" value={summary.onTrack} variant="success" />
          <StatCard
            label="SLA Compliance"
            value={`${summary.slaCompliance}%`}
            variant={summary.slaCompliance >= 80 ? "success" : "danger"}
          />
        </div>
      </div>

      {/* KPI Row 2 */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Avg Resolution Time" value={formatDuration(summary.avgResolutionTime)} variant="default" />
        <StatCard label="Avg Breach Duration" value={formatDuration(summary.avgBreachDuration)} variant="danger" />
        <StatCard label="At Risk" value={summary.atRisk} variant="warning" />
        <StatCard label="In Progress" value={summary.inProgress} variant="info" />
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Breaches by Priority */}
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">
            Breaches by Priority
          </h2>
          <div className="space-y-4">
            {breachesByPriority.map((item) => (
              <div key={item.priority}>
                <div className="mb-2 flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2.5">
                    <Badge variant={priorityBadgeVariant[item.priority] ?? "default"}>
                      {item.priority}
                    </Badge>
                    <span className="text-slate-500 tabular-nums">
                      {item.breached} / {item.total}
                    </span>
                  </div>
                  <span className="font-semibold text-slate-900 tabular-nums">{item.percentage}%</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-red-400 to-red-500 transition-all duration-500"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Breaches by Group */}
        <div className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">
            Breaches by Assignee Group
          </h2>
          {breachesByGroup.length > 0 ? (
            <div className="space-y-4">
              {breachesByGroup.map((item) => (
                <div key={item.name}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-slate-900">{item.name}</span>
                    <span className="font-semibold tabular-nums">{item.percentage}%</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-indigo-500 transition-all duration-500"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <p className="text-sm text-slate-500">No breach data yet</p>
              <p className="mt-1 text-xs text-slate-400">Data will appear as tickets are tracked</p>
            </div>
          )}
        </div>
      </div>

      {/* Status Distribution */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">
          Ticket Status Distribution
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(statusDistribution).map(([status, count]) => (
            <div
              key={status}
              className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center transition-colors hover:border-indigo-200 hover:bg-indigo-50/30"
            >
              <p className="text-3xl font-bold tracking-tight text-slate-900">{count}</p>
              <p className="mt-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                {status.replace("_", " ")}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}