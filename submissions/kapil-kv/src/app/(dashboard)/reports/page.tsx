"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { formatDuration, priorityColor, slaStatusColor } from "@/utils/formatters";

interface ReportData {
  summary: {
    total: number;
    breached: number;
    byPriority: Array<{
      priority: string;
      total: number;
      breached: number;
      percentage: number;
    }>;
    byGroup: Array<{
      name: string;
      total: number;
      breached: number;
      percentage: number;
    }>;
  };
}

export default function ReportsPage() {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [priorityFilter, setPriorityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchReport();
  }, []);

  async function fetchReport() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (priorityFilter) params.set("priority", priorityFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (dateFrom) params.set("dateFrom", dateFrom);
      if (dateTo) params.set("dateTo", dateTo);

      const res = await fetch(`/api/reports/sla?${params}`);
      const json = await res.json();
      if (json.success) setData(json.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (priorityFilter) params.set("priority", priorityFilter);
      if (statusFilter) params.set("status", statusFilter);
      if (dateFrom) params.set("dateFrom", dateFrom);
      if (dateTo) params.set("dateTo", dateTo);

      const res = await fetch(`/api/reports/sla/export?${params}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sla-report-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SLA Reports</h1>
        <Button onClick={handleExport} loading={exporting}>
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select
          options={[
            { value: "P1", label: "P1" },
            { value: "P2", label: "P2" },
            { value: "P3", label: "P3" },
            { value: "P4", label: "P4" },
          ]}
          placeholder="All Priorities"
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="w-36"
        />
        <Select
          options={[
            { value: "OPEN", label: "Open" },
            { value: "IN_PROGRESS", label: "In Progress" },
            { value: "ON_HOLD", label: "On Hold" },
            { value: "RESOLVED", label: "Resolved" },
          ]}
          placeholder="All Statuses"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="w-40"
        />
        <input
          type="date"
          className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          placeholder="From"
        />
        <input
          type="date"
          className="rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          placeholder="To"
        />
        <Button variant="secondary" onClick={fetchReport}>
          Apply Filters
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
        </div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Summary */}
          <div className="rounded-lg border border-[var(--border)] p-4 lg:col-span-2">
            <h2 className="mb-3 text-lg font-semibold">Summary</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-md bg-[var(--muted)] p-3 text-center">
                <p className="text-2xl font-bold">{data.summary.total}</p>
                <p className="text-xs text-[var(--muted-foreground)]">Total Tickets</p>
              </div>
              <div className="rounded-md bg-[var(--muted)] p-3 text-center">
                <p className="text-2xl font-bold text-[var(--danger)]">{data.summary.breached}</p>
                <p className="text-xs text-[var(--muted-foreground)]">Breached</p>
              </div>
              <div className="rounded-md bg-[var(--muted)] p-3 text-center">
                <p className="text-2xl font-bold text-[var(--success)]">
                  {data.summary.total > 0
                    ? Math.round(((data.summary.total - data.summary.breached) / data.summary.total) * 100)
                    : 100}%
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">Compliance</p>
              </div>
              <div className="rounded-md bg-[var(--muted)] p-3 text-center">
                <p className="text-2xl font-bold">
                  {data.summary.total > 0
                    ? Math.round((data.summary.breached / data.summary.total) * 100)
                    : 0}%
                </p>
                <p className="text-xs text-[var(--muted-foreground)]">Breach Rate</p>
              </div>
            </div>
          </div>

          {/* Breaches by Priority */}
          <div className="rounded-lg border border-[var(--border)] p-4">
            <h2 className="mb-3 text-lg font-semibold">Breaches by Priority</h2>
            <div className="space-y-3">
              {data.summary.byPriority.map((item) => (
                <div key={item.priority}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <Badge className={priorityColor(item.priority)}>{item.priority}</Badge>
                    <span className="font-medium">{item.percentage}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-[var(--muted)]">
                    <div
                      className="h-2 rounded-full bg-[var(--danger)]"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Breaches by Group */}
          <div className="rounded-lg border border-[var(--border)] p-4">
            <h2 className="mb-3 text-lg font-semibold">Breaches by Group</h2>
            {data.summary.byGroup.length > 0 ? (
              <div className="space-y-3">
                {data.summary.byGroup.map((item) => (
                  <div key={item.name}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span>{item.name}</span>
                      <span className="font-medium">{item.percentage}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-[var(--muted)]">
                      <div
                        className="h-2 rounded-full bg-[var(--danger)]"
                        style={{ width: `${item.percentage}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">No data.</p>
            )}
          </div>
        </div>
      ) : (
        <p className="text-center text-[var(--muted-foreground)]">No data available.</p>
      )}
    </div>
  );
}