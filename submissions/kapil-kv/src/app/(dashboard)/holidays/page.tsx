"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { formatDateOnly } from "@/utils/formatters";

interface Holiday {
  _id: string;
  date: string;
  name: string;
  isActive: boolean;
}

export default function HolidaysPage() {
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);

  const [newName, setNewName] = useState("");
  const [newDate, setNewDate] = useState("");
  const [addError, setAddError] = useState("");
  const [addLoading, setAddLoading] = useState(false);

  useEffect(() => {
    fetchHolidays();
  }, []);

  async function fetchHolidays() {
    try {
      const res = await fetch("/api/holidays?includeInactive=true");
      const json = await res.json();
      if (json.success) setHolidays(json.data.holidays);
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
      const res = await fetch("/api/holidays", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, date: newDate }),
      });

      const json = await res.json();
      if (json.success) {
        setShowAdd(false);
        setNewName("");
        setNewDate("");
        fetchHolidays();
      } else {
        setAddError(json.error?.message || "Failed to add holiday.");
      }
    } catch {
      setAddError("Unable to create holiday.");
    } finally {
      setAddLoading(false);
    }
  }

  async function toggleActive(holiday: Holiday) {
    await fetch(`/api/holidays/${holiday._id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ isActive: !holiday.isActive }),
    });
    fetchHolidays();
  }

  async function handleDelete(holidayId: string) {
    if (!confirm("Are you sure you want to delete this holiday?")) return;
    await fetch(`/api/holidays/${holidayId}`, { method: "DELETE" });
    fetchHolidays();
  }

  if (loading) {
    return <div className="flex justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--border)] border-t-[var(--primary)]" />
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Holidays</h1>
        <Button onClick={() => setShowAdd(true)}>+ Add Holiday</Button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead className="border-b border-[var(--border)] bg-[var(--muted)]">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Date</th>
              <th className="px-4 py-3 text-left font-medium">Name</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {holidays.map((h) => (
              <tr key={h._id}>
                <td className="px-4 py-3">{formatDateOnly(h.date)}</td>
                <td className="px-4 py-3">{h.name}</td>
                <td className="px-4 py-3">
                  <Badge variant={h.isActive ? "success" : "neutral"}>
                    {h.isActive ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <Button size="sm" variant="ghost" onClick={() => toggleActive(h)}>
                      {h.isActive ? "Deactivate" : "Activate"}
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => handleDelete(h._id)}>
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Holiday">
        <div className="space-y-4">
          <Input
            label="Holiday Name"
            placeholder="e.g., New Year"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <Input
            label="Date"
            type="date"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
          />
          {addError && <p className="text-sm text-[var(--danger)]">{addError}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={handleAdd} loading={addLoading} disabled={!newName || !newDate}>Add</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}