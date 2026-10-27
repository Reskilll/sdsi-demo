"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import {
  formatDate,
  formatDuration,
  priorityColor,
  statusColor,
  slaStatusColor,
} from "@/utils/formatters";

interface TicketDetail {
  _id: string;
  ticketNumber: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  assigneeGroup?: { _id: string; name: string } | null;
  assigneeGroups?: Array<{ _id: string; name: string }>;
  createdAt: string;
  resolvedAt?: string | null;
  statusHistory: Array<{
    status: string;
    timestamp: string;
    reason?: string;
  }>;
  slaResult?: {
    elapsedBusinessMinutes: number;
    slaTargetMinutes: number;
    dueBy: string;
    isBreached: boolean;
    breachMinutes: number;
    remainingBusinessMinutes: number;
    slaStatus: string;
    isProvisional: boolean;
  };
}

function IconBack() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </svg>
  );
}

function IconEdit() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  );
}

function IconClock() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconFile() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function IconTimeline() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="2" x2="12" y2="22" />
      <polyline points="4 10 12 16 20 10" />
    </svg>
  );
}

export default function TicketDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [statusModal, setStatusModal] = useState(false);
  const [newStatus, setNewStatus] = useState("");
  const [statusReason, setStatusReason] = useState("");
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState("");

  const [editModal, setEditModal] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editPriority, setEditPriority] = useState("");
  const [editGroup, setEditGroup] = useState("");
  const [editLoading, setEditLoading] = useState(false);

  const id = params.id as string;

  useEffect(() => {
    fetchTicket();
  }, [id]);

  async function fetchTicket() {
    try {
      setLoading(true);
      const res = await fetch(`/api/tickets/${id}`);
      const json = await res.json();

      if (json.success) {
        const slaRes = await fetch(`/api/reports/sla`);
        const slaJson = await slaRes.json();
        const slaTicket = slaJson.success
          ? slaJson.data.tickets?.find((t: any) => t._id === id)
          : null;

        setTicket({
          ...json.data.ticket,
          slaResult: slaTicket?.slaResult || null,
        });
      } else {
        setError(json.error?.message || "Ticket not found.");
      }
    } catch {
      setError("Unable to load ticket.");
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange() {
    if (!newStatus) return;
    setStatusLoading(true);
    setStatusError("");

    try {
      const res = await fetch(`/api/tickets/${id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: newStatus,
          reason: statusReason,
        }),
      });

      const json = await res.json();
      if (json.success) {
        setStatusModal(false);
        setNewStatus("");
        setStatusReason("");
        fetchTicket();
      } else {
        setStatusError(json.error?.message || "Failed to update status.");
      }
    } catch {
      setStatusError("Unable to update status.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function handleEdit() {
    setEditLoading(true);
    try {
      const res = await fetch(`/api/tickets/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle,
          priority: editPriority,
          assigneeGroup: editGroup || null,
        }),
      });

      const json = await res.json();
      if (json.success) {
        setEditModal(false);
        fetchTicket();
      }
    } catch {
      // Handle silently
    } finally {
      setEditLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
        <p className="mt-3 text-sm text-[var(--muted-foreground)]">Loading ticket...</p>
      </div>
    );
  }

  if (error && !ticket) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--danger-light)]">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <p className="text-sm font-medium text-[var(--danger-foreground)]">{error}</p>
        <Button variant="secondary" onClick={() => router.push("/tickets")} className="mt-4 gap-1.5">
          <IconBack />
          Back to Tickets
        </Button>
      </div>
    );
  }

  if (!ticket) return null;

  const sla = ticket.slaResult;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <button
            onClick={() => router.push("/tickets")}
            className="mb-3 inline-flex items-center gap-1.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors"
          >
            <IconBack />
            Back to Tickets
          </button>
          <h1 className="text-xl font-bold tracking-tight text-[var(--foreground)]">{ticket.title}</h1>
          <p className="mt-1.5 inline-flex items-center gap-2 font-mono text-xs font-medium text-[var(--primary)] bg-indigo-50 px-2.5 py-1 rounded-md">
            {ticket.ticketNumber}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setEditTitle(ticket.title);
              setEditPriority(ticket.priority);
              setEditGroup(ticket.assigneeGroup?._id || "");
              setEditModal(true);
            }}
            className="gap-1.5"
          >
            <IconEdit />
            Edit
          </Button>
          {ticket.status !== "RESOLVED" && (
            <Button
              size="sm"
              onClick={() => {
                setNewStatus("");
                setStatusReason("");
                setStatusError("");
                setStatusModal(true);
              }}
              className="gap-1.5"
            >
              <IconRefresh />
              Change Status
            </Button>
          )}
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Priority", content: <Badge className={priorityColor(ticket.priority)} size="md">{ticket.priority}</Badge> },
          { label: "Status", content: <Badge className={statusColor(ticket.status)} size="md">{ticket.status.replace("_", " ")}</Badge> },
          { label: "Assignee Group", content: <p className="font-medium text-sm">{ticket.assigneeGroup?.name || "Unassigned"}</p> },
          { label: "Created", content: <p className="font-medium text-sm">{formatDate(ticket.createdAt)}</p> },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-[var(--border)] bg-white p-4 shadow-[var(--shadow-sm)]">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)] mb-1.5">{item.label}</p>
            {item.content}
          </div>
        ))}
      </div>

      {/* Description */}
      {ticket.description && (
        <div className="rounded-xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-sm)]">
          <div className="mb-3 flex items-center gap-2">
            <span className="text-[var(--muted-foreground)]"><IconFile /></span>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--foreground)]">Description</h3>
          </div>
          <p className="text-sm text-[var(--muted-foreground)] whitespace-pre-wrap leading-relaxed">
            {ticket.description}
          </p>
        </div>
      )}

      {/* SLA Details */}
      {sla && (
        <div className="rounded-xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-sm)]">
          <div className="mb-4 flex items-center gap-2">
            <span className="text-[var(--muted-foreground)]"><IconClock /></span>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--foreground)]">
              SLA Information
            </h3>
            {sla.isProvisional && (
              <span className="ml-auto rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                Provisional — ticket on hold
              </span>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg bg-[var(--muted)] p-3">
              <p className="text-xs text-[var(--muted-foreground)] mb-1">SLA Status</p>
              <Badge className={slaStatusColor(sla.slaStatus)} size="md">
                {sla.slaStatus}
              </Badge>
            </div>
            <div className="rounded-lg bg-[var(--muted)] p-3">
              <p className="text-xs text-[var(--muted-foreground)] mb-1">Elapsed (Business)</p>
              <p className="font-semibold text-[var(--foreground)]">{formatDuration(sla.elapsedBusinessMinutes)}</p>
            </div>
            <div className="rounded-lg bg-[var(--muted)] p-3">
              <p className="text-xs text-[var(--muted-foreground)] mb-1">SLA Target</p>
              <p className="font-semibold text-[var(--foreground)]">{formatDuration(sla.slaTargetMinutes)}</p>
            </div>
            <div className="rounded-lg bg-[var(--muted)] p-3">
              <p className="text-xs text-[var(--muted-foreground)] mb-1">Due By</p>
              <p className="font-semibold text-[var(--foreground)]">{formatDate(sla.dueBy)}</p>
            </div>
            {sla.isBreached && (
              <div className="rounded-lg bg-[var(--danger-light)] p-3">
                <p className="text-xs text-[var(--danger-foreground)] mb-1">Breach Duration</p>
                <p className="font-semibold text-[var(--danger)]">{formatDuration(sla.breachMinutes)}</p>
              </div>
            )}
            {sla.remainingBusinessMinutes > 0 && ticket.status !== "RESOLVED" && (
              <div className="rounded-lg bg-[var(--success-light)] p-3">
                <p className="text-xs text-[var(--success-foreground)] mb-1">Remaining</p>
                <p className="font-semibold text-[var(--success)]">{formatDuration(sla.remainingBusinessMinutes)}</p>
              </div>
            )}
            {ticket.resolvedAt && (
              <div className="rounded-lg bg-[var(--muted)] p-3">
                <p className="text-xs text-[var(--muted-foreground)] mb-1">Resolved At</p>
                <p className="font-semibold text-[var(--foreground)]">{formatDate(ticket.resolvedAt)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status History */}
      <div className="rounded-xl border border-[var(--border)] bg-white p-5 shadow-[var(--shadow-sm)]">
        <div className="mb-4 flex items-center gap-2">
          <span className="text-[var(--muted-foreground)]"><IconTimeline /></span>
          <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--foreground)]">Status Timeline</h3>
        </div>
        <div className="space-y-0">
          {[...ticket.statusHistory].reverse().map((event, i) => (
            <div key={i} className="relative flex gap-4 pb-5 last:pb-0">
              {/* Timeline line */}
              {i < ticket.statusHistory.length - 1 && (
                <div className="absolute left-[7px] top-4 bottom-0 w-px bg-[var(--border)]" />
              )}
              <div className="relative mt-1.5 h-3.5 w-3.5 flex-shrink-0 rounded-full border-2 border-[var(--primary)] bg-white" />
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={statusColor(event.status)}>{event.status.replace("_", " ")}</Badge>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                {event.reason && (
                  <p className="mt-1.5 text-sm text-[var(--muted-foreground)] leading-relaxed">{event.reason}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status Change Modal */}
      <Modal
        open={statusModal}
        onClose={() => setStatusModal(false)}
        title="Change Status"
      >
        <div className="space-y-4">
          <Select
            label="New Status"
            options={[
              ...(ticket.status !== "RESOLVED" ? [
                ...(ticket.status !== "IN_PROGRESS" ? [{ value: "IN_PROGRESS", label: "In Progress" }] : []),
                ...(ticket.status !== "ON_HOLD" ? [{ value: "ON_HOLD", label: "On Hold" }] : []),
                { value: "RESOLVED", label: "Resolved" },
                { value: "OPEN", label: "Open" },
              ] : []),
            ]}
            placeholder="Select status"
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
          />
          <Input
            label="Reason (optional)"
            placeholder="Reason for status change"
            value={statusReason}
            onChange={(e) => setStatusReason(e.target.value)}
          />
          {statusError && (
            <div className="rounded-lg bg-[var(--danger-light)] px-3 py-2 text-sm text-[var(--danger-foreground)]">{statusError}</div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setStatusModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleStatusChange} loading={statusLoading} disabled={!newStatus}>
              Update Status
            </Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal
        open={editModal}
        onClose={() => setEditModal(false)}
        title="Edit Ticket"
      >
        <div className="space-y-4">
          <Input
            label="Title"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
          />
          <Select
            label="Priority"
            options={[
              { value: "P1", label: "P1 — Critical (4h)" },
              { value: "P2", label: "P2 — High (8h)" },
              { value: "P3", label: "P3 — Medium (24h)" },
              { value: "P4", label: "P4 — Low (72h)" },
            ]}
            value={editPriority}
            onChange={(e) => setEditPriority(e.target.value)}
          />
          <Select
            label="Assignee Group"
            options={[]}
            placeholder="Select group"
            value={editGroup}
            onChange={(e) => setEditGroup(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setEditModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleEdit} loading={editLoading}>
              Save Changes
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}