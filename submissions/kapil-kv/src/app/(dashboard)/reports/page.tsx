"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { priorityColor } from "@/utils/formatters";

interface ReportData {
  summary: {
    total: number;
    breached: number;
    byPriority: Array<{ priority: string; total: number; breached: number; percentage: number }>;
    byGroup: Array<{ name: string; total: number; breached: number; percentage: number }>;
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

  useEffect(() => { fetchReport(); }, []);

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
    } catch { /* silent */ } finally { setLoading(false); }
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
    } catch { /* silent */ } finally { setExporting(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">SLA Reports</h1>
          <p className="mt-0.5 text-sm text-slate-500">Analyze SLA performance and compliance trends</p>
        </div>
        <Button onClick={handleExport} loading={exporting}>Export CSV</Button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
        <span className="hidden items-center gap-1.5 text-sm font-medium text-slate-500 sm:flex">Filters:</span>
        <Select options={[{ value: "P1", label: "P1 — Critical" }, { value: "P2", label: "P2 — High" }, { value: "P3", label: "P3 — Medium" }, { value: "P4", label: "P4 — Low" }]} placeholder="All Priorities" value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="w-40" />
        <Select options={[{ value: "OPEN", label: "Open" }, { value: "IN_PROGRESS", label: "In Progress" }, { value: "ON_HOLD", label: "On Hold" }, { value: "RESOLVED", label: "Resolved" }]} placeholder="All Statuses" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-44" />
        <input type="date" className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/15" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <span className="text-xs text-slate-400">to</span>
        <input type="date" className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/15" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        <Button variant="secondary" size="sm" onClick={fetchReport}>Apply Filters</Button>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
          <p className="mt-3 text-sm text-slate-500">Generating report...</p>
        </div>
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-6 lg:col-span-2">
            <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">Summary</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
                <p className="text-3xl font-bold tracking-tight text-slate-900">{data.summary.total}</p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Total</p>
              </div>
              <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
                <p className="text-3xl font-bold tracking-tight text-red-700">{data.summary.breached}</p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-red-600">Breached</p>
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
                <p className="text-3xl font-bold tracking-tight text-emerald-700">
                  {data.summary.total > 0 ? Math.round(((data.summary.total - data.summary.breached) / data.summary.total) * 100) : 100}%
                </p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-emerald-600">Compliance</p>
              </div>
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center">
                <p className="text-3xl font-bold tracking-tight text-amber-700">
                  {data.summary.total > 0 ? Math.round((data.summary.breached / data.summary.total) * 100) : 0}%
                </p>
                <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-amber-600">Breach Rate</p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">Breaches by Priority</h2>
            <div className="space-y-4">
              {data.summary.byPriority.map((item) => (
                <div key={item.priority}>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <Badge className={priorityColor(item.priority)}>{item.priority}</Badge>
                    <span className="font-semibold tabular-nums text-slate-900">{item.percentage}%</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-gradient-to-r from-red-400 to-red-500 transition-all duration-500" style={{ width: `${item.percentage}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <h2 className="mb-5 text-sm font-semibold uppercase tracking-wider text-slate-700">Breaches by Group</h2>
            {data.summary.byGroup.length > 0 ? (
              <div className="space-y-4">
                {data.summary.byGroup.map((item) => (
                  <div key={item.name}>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-900">{item.name}</span>
                      <span className="font-semibold tabular-nums">{item.percentage}%</span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-gradient-to-r from-indigo-400 to-indigo-500 transition-all duration-500" style={{ width: `${item.percentage}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <p className="text-sm text-slate-500">No group data available.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20">
          <p className="text-sm text-slate-500">No data available for the selected filters.</p>
        </div>
      )}
    </div>
  );
}