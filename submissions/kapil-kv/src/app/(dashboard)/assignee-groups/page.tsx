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

  useEffect(() => { fetchGroups(); }, []);

  async function fetchGroups() {
    try {
      const res = await fetch("/api/assignee-groups?includeInactive=true");
      const json = await res.json();
      if (json.success) setGroups(json.data.groups);
    } catch { /* silent */ } finally { setLoading(false); }
  }

  async function handleAdd() {
    setAddError(""); setAddLoading(true);
    try {
      const res = await fetch("/api/assignee-groups", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName, description: newDescription }) });
      const json = await res.json();
      if (json.success) { setShowAdd(false); setNewName(""); setNewDescription(""); fetchGroups(); }
      else setAddError(json.error?.message || "Failed to create group.");
    } catch { setAddError("Unable to create group."); } finally { setAddLoading(false); }
  }

  async function toggleActive(group: Group) {
    await fetch(`/api/assignee-groups/${group._id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ isActive: !group.isActive }) });
    fetchGroups();
  }

  async function handleDelete(groupId: string, groupName: string) {
    if (!confirm(`Delete group "${groupName}"?`)) return;
    const res = await fetch(`/api/assignee-groups/${groupId}`, { method: "DELETE" });
    const json = await res.json();
    if (!json.success) alert(json.error?.message || "Cannot delete this group.");
    fetchGroups();
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
        <p className="mt-3 text-sm text-slate-500">Loading groups...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Assignee Groups</h1>
          <p className="mt-0.5 text-sm text-slate-500">Manage teams for ticket assignment</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add Group</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {groups.map((group) => (
          <div key={group._id} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-slate-900">{group.name}</p>
                  <Badge variant={group.isActive ? "success" : "neutral"}>{group.isActive ? "Active" : "Inactive"}</Badge>
                </div>
                <p className="mt-1 text-sm text-slate-500">{group.description || "No description"}</p>
              </div>
            </div>
            <div className="flex flex-shrink-0 gap-1.5">
              <Button size="sm" variant="ghost" onClick={() => toggleActive(group)}>{group.isActive ? "Deactivate" : "Activate"}</Button>
              <Button size="sm" variant="danger" onClick={() => handleDelete(group._id, group.name)}>Delete</Button>
            </div>
          </div>
        ))}
        {groups.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-slate-200 bg-white py-12">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-900">No groups defined yet</p>
            <p className="mt-1 text-xs text-slate-500">Create your first assignee group to get started</p>
          </div>
        )}
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Assignee Group">
        <div className="space-y-4">
          <Input label="Group Name" placeholder="e.g., Network Team" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <Input label="Description (optional)" placeholder="Brief description" value={newDescription} onChange={(e) => setNewDescription(e.target.value)} />
          {addError && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{addError}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={handleAdd} loading={addLoading} disabled={!newName}>Create Group</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}