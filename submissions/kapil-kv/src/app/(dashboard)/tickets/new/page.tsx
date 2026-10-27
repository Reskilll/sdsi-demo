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
      // silent
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
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <button
          onClick={() => router.push("/tickets")}
          className="mb-3 inline-flex items-center gap-1.5 text-sm text-slate-500 transition-colors hover:text-indigo-600"
        >
          ← Back to Tickets
        </button>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Create New Ticket</h1>
        <p className="mt-0.5 text-sm text-slate-500">Fill in the details to create a new service desk ticket</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 rounded-xl border border-slate-200 bg-white p-6">
        <Input
          label="Title *"
          placeholder="Brief description of the issue"
          error={errors.title?.message}
          {...register("title", { required: "Title is required", maxLength: { value: 500, message: "Max 500 characters" } })}
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Description</label>
          <textarea
            className="w-full min-h-[120px] resize-y rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/15"
            placeholder="Detailed description (optional)"
            {...register("description")}
          />
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
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
        </div>

        {serverError && (
          <div className="flex items-center gap-2.5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {serverError}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <Button type="submit" loading={loading}>Create Ticket</Button>
          <Button type="button" variant="secondary" onClick={() => router.back()}>Cancel</Button>
        </div>
      </form>
    </div>
  );
}