"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { formatDate, priorityColor, statusColor } from "@/utils/formatters";

interface Ticket {
  _id: string;
  ticketNumber: string;
  title: string;
  priority: string;
  status: string;
  assigneeGroup?: { _id: string; name: string } | null;
  createdAt: string;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export default function TicketsPage() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [pagination, setPagination] = useState<Pagination | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", "20");
      if (search) params.set("search", search);
      if (priorityFilter) params.set("priority", priorityFilter);
      if (statusFilter) params.set("status", statusFilter);

      const res = await fetch(`/api/tickets?${params}`);
      const json = await res.json();
      if (json.success) {
        setTickets(json.data.tickets);
        setPagination(json.data.pagination);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [page, search, priorityFilter, statusFilter]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Tickets</h1>
          <p className="mt-0.5 text-sm text-slate-500">Manage and track service desk tickets</p>
        </div>
        <Link href="/tickets/new">
          <Button>+ New Ticket</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
        <div className="relative w-full sm:w-64">
          <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </span>
          <input
            placeholder="Search tickets..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full rounded-lg border border-slate-300 bg-slate-50 py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/15"
          />
        </div>
        <Select
          options={[
            { value: "P1", label: "P1 — Critical" },
            { value: "P2", label: "P2 — High" },
            { value: "P3", label: "P3 — Medium" },
            { value: "P4", label: "P4 — Low" },
          ]}
          placeholder="All Priorities"
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
          className="w-40"
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
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="w-44"
        />
        <Button variant="secondary" size="sm" onClick={fetchTickets}>
          Refresh
        </Button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
          <p className="mt-3 text-sm text-slate-500">Loading tickets...</p>
        </div>
      ) : tickets.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-16">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-slate-400">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-900">No tickets found</p>
          <p className="mt-1 text-xs text-slate-500">Adjust your filters or create a new ticket</p>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/80">
                    {["Ticket #", "Title", "Priority", "Status", "Group", "Created"].map((h) => (
                      <th key={h} className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tickets.map((ticket) => (
                    <tr
                      key={ticket._id}
                      className="cursor-pointer transition-colors hover:bg-indigo-50/30"
                      onClick={() => router.push(`/tickets/${ticket._id}`)}
                    >
                      <td className="px-5 py-3.5 font-mono text-xs font-medium text-indigo-600">{ticket.ticketNumber}</td>
                      <td className="px-5 py-3.5 max-w-xs truncate font-medium text-slate-900">{ticket.title}</td>
                      <td className="px-5 py-3.5"><Badge className={priorityColor(ticket.priority)}>{ticket.priority}</Badge></td>
                      <td className="px-5 py-3.5"><Badge className={statusColor(ticket.status)}>{ticket.status.replace("_", " ")}</Badge></td>
                      <td className="px-5 py-3.5 text-slate-500">{ticket.assigneeGroup?.name || "—"}</td>
                      <td className="px-5 py-3.5 whitespace-nowrap text-xs text-slate-500">{formatDate(ticket.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {pagination && pagination.totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">
                Showing {Math.min((pagination.page - 1) * pagination.limit + 1, pagination.total)}–{Math.min(pagination.page * pagination.limit, pagination.total)} of {pagination.total}
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Previous</Button>
                <Button variant="secondary" size="sm" disabled={page >= pagination.totalPages} onClick={() => setPage(page + 1)}>Next →</Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}