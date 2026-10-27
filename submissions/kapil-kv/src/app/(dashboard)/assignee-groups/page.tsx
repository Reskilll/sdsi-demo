"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";

interface Group {
  _id: string;
  name: string;
  description?: string;
  isActive: boolean;
}

export default function AssigneeGroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");

  useEffect(() => {
    fetchGroups();
  }, []);

  async function fetchGroups() {
    try {
      const res = await fetch("/api/assignee-groups?includeInactive=true");
      const json = await res.json();
      if (json.success) setGroups(json.data.groups);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    setAddError("");
    setAddLoading(true);
    try {
      const res = await fetch("/api/assignee-groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, description: newDescription }),
      });
      const json = await res.json();
      if (json.success) {
        setShowAdd(false);
        setNewName("");
        setNewDescription("");
        fetchGroups();
      } else {
        setAddError(json.error?.message || "Failed to create group.");
      }
    } catch {
      setAddError("Unable to create group.");
    } finally {
      setAddLoading(false);
    }
  }

  async function toggleActive(group: Group) {
    await fetch(`/api/assignee-groups/${group._id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isActive: !group.isActive }),
    });
    fetchGroups();
  }

  async function handleDelete(groupId: string, groupName: string) {
    if (!confirm(`Delete group "${groupName}"?`)) return;
    const res = await fetch(`/api/assignee-groups/${groupId}`, { method: "DELETE" });
    const json = await res.json();
    if (!json.success) {
      alert(json.error?.message || "Cannot delete this group.");
    }
    fetchGroups();
  }

  if (loading) {
    return <div className="flex justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Assignee Groups</h1>
        <Button onClick={() => setShowAdd(true)}>+ Add Group</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {groups.map((group) => (
          <div key={group._id} className="flex items-start justify-between rounded-lg border border-[var(--border)] p-4">
            <div>
              <div className="flex items-center gap-2">
                <p className="font-medium">{group.name}</p>
                <Badge variant={group.isActive ? "success" : "neutral"}>
                  {group.isActive ? "Active" : "Inactive"}
                </Badge>
              </div>
              {group.description && (
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">{group.description}</p>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={() => toggleActive(group)}>
                {group.isActive ? "Deactivate" : "Activate"}
              </Button>
              <Button size="sm" variant="danger" onClick={() => handleDelete(group._id, group.name)}>
                Delete
              </Button>
            </div>
          </div>
        ))}
        {groups.length === 0 && (
          <p className="text-[var(--muted-foreground)]">No groups defined yet.</p>
        )}
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Assignee Group">
        <div className="space-y-4">
          <Input
            label="Group Name"
            placeholder="e.g., Network Team"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Input
            label="Description (optional)"
            placeholder="Brief description"
            value={newDescription}
            onChange={(e) => setNewDescription(e.target.value)}
          />
          {addError && <p className="text-sm text-[var(--danger)]">{addError}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={handleAdd} loading={addLoading} disabled={!newName}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}