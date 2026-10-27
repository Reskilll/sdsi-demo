"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";

interface Policy {
  _id: string;
  priority: string;
  targetBusinessHours: number;
  isActive: boolean;
}

const priorityBadgeVariant: Record<string, "danger" | "warning" | "info" | "default"> = {
  P1: "danger", P2: "warning", P3: "info", P4: "default",
};

export default function SlaPoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<number>(0);
  const [saving, setSaving] = useState(false);

  useEffect(() => { fetchPolicies(); }, []);

  async function fetchPolicies() {
    try {
      const res = await fetch("/api/sla-policies");
      const json = await res.json();
      if (json.success) setPolicies(json.data.policies);
    } catch { /* silent */ } finally { setLoading(false); }
  }

  async function handleSave(policyId: string) {
    setSaving(true);
    try {
      await fetch(`/api/sla-policies/${policyId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targetBusinessHours: editValue }),
      });
      setEditingId(null);
      fetchPolicies();
    } catch { /* silent */ } finally { setSaving(false); }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
        <p className="mt-3 text-sm text-slate-500">Loading policies...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">SLA Policies</h1>
        <p className="mt-0.5 text-sm text-slate-500">Configure target resolution times for each priority level</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {policies.map((policy) => (
          <div key={policy._id} className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <Badge variant={priorityBadgeVariant[policy.priority] ?? "default"} size="md">
                Priority {policy.priority}
              </Badge>
              <Badge variant={policy.isActive ? "success" : "neutral"}>
                {policy.isActive ? "Active" : "Inactive"}
              </Badge>
            </div>

            {editingId === policy._id ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Input type="number" min="0.25" step="0.5" value={editValue} onChange={(e) => setEditValue(Number(e.target.value))} className="w-28" />
                  <span className="text-sm text-slate-500">business hours</span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleSave(policy._id)} loading={saving}>Save</Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>Cancel</Button>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-3xl font-bold tracking-tight text-slate-900">{policy.targetBusinessHours}h</p>
                <p className="mt-1 text-xs text-slate-500">Target SLA: {policy.targetBusinessHours * 60} business minutes</p>
                <Button size="sm" variant="secondary" className="mt-4" onClick={() => { setEditingId(policy._id); setEditValue(policy.targetBusinessHours); }}>
                  Edit Target
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}