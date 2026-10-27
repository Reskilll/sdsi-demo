"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";

interface AssigneeGroup {
  _id: string;
  name: string;
}

interface TicketFormData {
  title: string;
  description: string;
  priority: string;
  assigneeGroup: string;
}

export default function NewTicketPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState("");
  const [groups, setGroups] = useState<AssigneeGroup[]>([]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TicketFormData>();

  useEffect(() => {
    fetchGroups();
  }, []);

  async function fetchGroups() {
    try {
      const res = await fetch("/api/assignee-groups");
      const json = await res.json();
      if (json.success) setGroups(json.data.groups);
    } catch {
      // Silently handle
    }
  }

  async function onSubmit(data: TicketFormData) {
    setServerError("");
    setLoading(true);

    try {
      const res = await fetch("/api/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const json = await res.json();
      if (json.success) {
        router.push(`/tickets/${json.data.ticket._id}`);
      } else {
        setServerError(json.error?.message || "Failed to create ticket.");
      }
    } catch {
      setServerError("Unable to create ticket.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <button
          onClick={() => router.push("/tickets")}
          className="mb-2 text-sm text-[var(--primary)] hover:underline"
        >
          ← Back to Tickets
        </button>
        <h1 className="text-2xl font-bold">Create New Ticket</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-lg border border-[var(--border)] p-6">
        <Input
          label="Title *"
          placeholder="Brief description of the issue"
          error={errors.title?.message}
          {...register("title", { required: "Title is required", maxLength: { value: 500, message: "Max 500 characters" } })}
        />

        <div>
          <label className="mb-1 block text-sm font-medium">Description</label>
          <textarea
            className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none focus:ring-1 focus:ring-[var(--primary)] min-h-[100px]"
            placeholder="Detailed description (optional)"
            {...register("description")}
          />
        </div>

        <Select
          label="Priority *"
          options={[
            { value: "P1", label: "P1 — Critical (4h SLA)" },
            { value: "P2", label: "P2 — High (8h SLA)" },
            { value: "P3", label: "P3 — Medium (24h SLA)" },
            { value: "P4", label: "P4 — Low (72h SLA)" },
          ]}
          placeholder="Select priority"
          error={errors.priority?.message}
          {...register("priority", { required: "Priority is required" })}
        />

        <Select
          label="Assignee Group"
          options={groups.map((g) => ({ value: g._id, label: g.name }))}
          placeholder="Select group (optional)"
          {...register("assigneeGroup")}
        />

        {serverError && (
          <div className="rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
            {serverError}
          </div>
        )}

        <div className="flex gap-3">
          <Button type="submit" loading={loading}>
            Create Ticket
          </Button>
          <Button type="button" variant="secondary" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}