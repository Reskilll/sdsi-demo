"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
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
  resolvedAt?: string | null;
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
      // Handle silently
    } finally {
      setLoading(false);
    }
  }, [page, search, priorityFilter, statusFilter]);

  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tickets</h1>
        <Link href="/tickets/new">
          <Button>+ New Ticket</Button>
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="w-full sm:w-64">
          <Input
            placeholder="Search tickets..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <Select
          options={[
            { value: "P1", label: "P1" },
            { value: "P2", label: "P2" },
            { value: "P3", label: "P3" },
            { value: "P4", label: "P4" },
          ]}
          placeholder="All Priorities"
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
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
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="w-40"
        />
        <Button variant="secondary" onClick={fetchTickets}>
          Refresh
        </Button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
        </div>
      ) : tickets.length === 0 ? (
        <div className="rounded-md border border-[var(--border)] p-12 text-center text-[var(--muted-foreground)]">
          No tickets found.
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border)] bg-[var(--muted)]">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Ticket #</th>
                  <th className="px-4 py-3 text-left font-medium">Title</th>
                  <th className="px-4 py-3 text-left font-medium">Priority</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-left font-medium">Group</th>
                  <th className="px-4 py-3 text-left font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {tickets.map((ticket) => (
                  <tr
                    key={ticket._id}
                    className="cursor-pointer hover:bg-[var(--muted)] transition-colors"
                    onClick={() => router.push(`/tickets/${ticket._id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs">{ticket.ticketNumber}</td>
                    <td className="px-4 py-3 max-w-xs truncate">{ticket.title}</td>
                    <td className="px-4 py-3">
                      <Badge className={priorityColor(ticket.priority)}>{ticket.priority}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge className={statusColor(ticket.status)}>
                        {ticket.status.replace("_", " ")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted-foreground)]">
                      {ticket.assigneeGroup?.name || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--muted-foreground)]">
                      {formatDate(ticket.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--muted-foreground)]">
                Showing {(pagination.page - 1) * pagination.limit + 1}–
                {Math.min(pagination.page * pagination.limit, pagination.total)} of{" "}
                {pagination.total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= pagination.totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}