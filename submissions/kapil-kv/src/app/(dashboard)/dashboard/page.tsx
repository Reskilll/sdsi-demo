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
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-md border border-red-300 bg-red-50 p-6 text-center dark:bg-red-900/20">
        <p className="text-red-600 dark:text-red-400">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-3 text-sm text-[var(--primary)] hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { summary, breachesByPriority, breachesByGroup, statusDistribution } = data;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
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

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Avg Resolution Time" value={formatDuration(summary.avgResolutionTime)} variant="default" />
        <StatCard label="Avg Breach Duration" value={formatDuration(summary.avgBreachDuration)} variant="danger" />
        <StatCard label="At Risk" value={summary.atRisk} variant="warning" />
        <StatCard label="In Progress" value={summary.inProgress} variant="info" />
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Breaches by Priority */}
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h2 className="mb-3 text-lg font-semibold">Breaches by Priority</h2>
          <div className="space-y-3">
            {breachesByPriority.map((item) => (
              <div key={item.priority}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant={
                      item.priority === "P1" ? "danger" :
                      item.priority === "P2" ? "warning" :
                      item.priority === "P3" ? "info" : "default"
                    }>
                      {item.priority}
                    </Badge>
                    <span className="text-[var(--muted-foreground)]">
                      {item.breached}/{item.total}
                    </span>
                  </div>
                  <span className="font-medium">{item.percentage}%</span>
                </div>
                <div className="h-2 rounded-full bg-[var(--muted)]">
                  <div
                    className="h-2 rounded-full bg-[var(--danger)] transition-all"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Breaches by Group */}
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h2 className="mb-3 text-lg font-semibold">Breaches by Assignee Group</h2>
          {breachesByGroup.length > 0 ? (
            <div className="space-y-3">
              {breachesByGroup.map((item) => (
                <div key={item.name}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span>{item.name}</span>
                    <span className="font-medium">{item.percentage}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--muted)]">
                    <div
                      className="h-2 rounded-full bg-[var(--danger)] transition-all"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">No data available.</p>
          )}
        </div>
      </div>

      {/* Status Distribution */}
      <div className="rounded-lg border border-[var(--border)] p-4">
        <h2 className="mb-3 text-lg font-semibold">Ticket Status Distribution</h2>
        <div className="grid grid-cols-4 gap-3 text-center">
          {Object.entries(statusDistribution).map(([status, count]) => (
            <div key={status} className="rounded-md bg-[var(--muted)] p-3">
              <p className="text-2xl font-bold">{count}</p>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                {status.replace("_", " ")}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}