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

export default function SlaPoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<number>(0);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchPolicies();
  }, []);

  async function fetchPolicies() {
    try {
      const res = await fetch("/api/sla-policies");
      const json = await res.json();
      if (json.success) setPolicies(json.data.policies);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
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
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="flex justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
    </div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">SLA Policies</h1>
      <div className="grid gap-4 sm:grid-cols-2">
        {policies.map((policy) => (
          <div key={policy._id} className="rounded-lg border border-[var(--border)] p-4">
            <div className="flex items-center justify-between mb-3">
              <Badge variant={
                policy.priority === "P1" ? "danger" :
                policy.priority === "P2" ? "warning" :
                policy.priority === "P3" ? "info" : "default"
              } size="md">
                {policy.priority}
              </Badge>
              <Badge variant={policy.isActive ? "success" : "neutral"}>{policy.isActive ? "Active" : "Inactive"}</Badge>
            </div>
            {editingId === policy._id ? (
              <div className="flex gap-2 items-center">
                <Input
                  type="number"
                  min="0.25"
                  step="0.5"
                  value={editValue}
                  onChange={(e) => setEditValue(Number(e.target.value))}
                  className="w-24"
                />
                <span className="text-sm text-[var(--muted-foreground)]">hours</span>
                <Button size="sm" onClick={() => handleSave(policy._id)} loading={saving}>
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <div>
                <p className="text-2xl font-bold">{policy.targetBusinessHours}h</p>
                <p className="text-xs text-[var(--muted-foreground)]">{policy.targetBusinessHours * 60} business minutes</p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-2"
                  onClick={() => {
                    setEditingId(policy._id);
                    setEditValue(policy.targetBusinessHours);
                  }}
                >
                  Edit
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}