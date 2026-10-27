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
        // Also fetch SLA calculation via reports
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
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
      </div>
    );
  }

  if (error && !ticket) {
    return (
      <div className="text-center py-20">
        <p className="text-[var(--danger)]">{error}</p>
        <Button variant="secondary" onClick={() => router.push("/tickets")} className="mt-4">
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
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.push("/tickets")}
            className="mb-2 text-sm text-[var(--primary)] hover:underline"
          >
            ← Back to Tickets
          </button>
          <h1 className="text-xl font-bold">{ticket.title}</h1>
          <p className="mt-1 font-mono text-sm text-[var(--muted-foreground)]">
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
          >
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
            >
              Change Status
            </Button>
          )}
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-[var(--border)] p-3">
          <p className="text-xs text-[var(--muted-foreground)]">Priority</p>
          <Badge className={priorityColor(ticket.priority)} size="md">
            {ticket.priority}
          </Badge>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-3">
          <p className="text-xs text-[var(--muted-foreground)]">Status</p>
          <Badge className={statusColor(ticket.status)} size="md">
            {ticket.status.replace("_", " ")}
          </Badge>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-3">
          <p className="text-xs text-[var(--muted-foreground)]">Assignee Group</p>
          <p className="mt-1 font-medium">{ticket.assigneeGroup?.name || "Unassigned"}</p>
        </div>
        <div className="rounded-lg border border-[var(--border)] p-3">
          <p className="text-xs text-[var(--muted-foreground)]">Created</p>
          <p className="mt-1 font-medium">{formatDate(ticket.createdAt)}</p>
        </div>
      </div>

      {/* Description */}
      {ticket.description && (
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h3 className="mb-2 text-sm font-medium">Description</h3>
          <p className="text-sm text-[var(--muted-foreground)] whitespace-pre-wrap">
            {ticket.description}
          </p>
        </div>
      )}

      {/* SLA Details */}
      {sla && (
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h3 className="mb-3 text-sm font-medium">
            SLA Information
            {sla.isProvisional && (
              <span className="ml-2 text-xs text-[var(--warning)]">(Provisional — ticket on hold)</span>
            )}
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">SLA Status</p>
              <Badge className={slaStatusColor(sla.slaStatus)} size="md">
                {sla.slaStatus}
              </Badge>
            </div>
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">Elapsed (Business)</p>
              <p className="font-medium">{formatDuration(sla.elapsedBusinessMinutes)}</p>
            </div>
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">SLA Target</p>
              <p className="font-medium">{formatDuration(sla.slaTargetMinutes)}</p>
            </div>
            <div>
              <p className="text-xs text-[var(--muted-foreground)]">Due By</p>
              <p className="font-medium">{formatDate(sla.dueBy)}</p>
            </div>
            {sla.isBreached && (
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Breach Duration</p>
                <p className="font-medium text-[var(--danger)]">
                  {formatDuration(sla.breachMinutes)}
                </p>
              </div>
            )}
            {sla.remainingBusinessMinutes > 0 && ticket.status !== "RESOLVED" && (
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Remaining</p>
                <p className="font-medium">{formatDuration(sla.remainingBusinessMinutes)}</p>
              </div>
            )}
            {ticket.resolvedAt && (
              <div>
                <p className="text-xs text-[var(--muted-foreground)]">Resolved At</p>
                <p className="font-medium">{formatDate(ticket.resolvedAt)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Status History */}
      <div className="rounded-lg border border-[var(--border)] p-4">
        <h3 className="mb-3 text-sm font-medium">Status Timeline</h3>
        <div className="space-y-3">
          {[...ticket.statusHistory].reverse().map((event, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="mt-1.5 h-2 w-2 rounded-full bg-[var(--primary)]" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <Badge className={statusColor(event.status)}>{event.status.replace("_", " ")}</Badge>
                  <span className="text-xs text-[var(--muted-foreground)]">
                    {formatDate(event.timestamp)}
                  </span>
                </div>
                {event.reason && (
                  <p className="mt-1 text-sm text-[var(--muted-foreground)]">{event.reason}</p>
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
            <p className="text-sm text-[var(--danger)]">{statusError}</p>
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
              { value: "P1", label: "P1 — Critical" },
              { value: "P2", label: "P2 — High" },
              { value: "P3", label: "P3 — Medium" },
              { value: "P4", label: "P4 — Low" },
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