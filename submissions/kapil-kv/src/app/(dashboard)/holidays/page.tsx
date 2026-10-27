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

  useEffect(() => { fetchHolidays(); }, []);

  async function fetchHolidays() {
    try {
      const res = await fetch("/api/holidays?includeInactive=true");
      const json = await res.json();
      if (json.success) setHolidays(json.data.holidays);
    } catch { /* silent */ } finally { setLoading(false); }
  }

  async function handleAdd() {
    setAddError(""); setAddLoading(true);
    try {
      const res = await fetch("/api/holidays", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName, date: newDate }) });
      const json = await res.json();
      if (json.success) { setShowAdd(false); setNewName(""); setNewDate(""); fetchHolidays(); }
      else setAddError(json.error?.message || "Failed to add holiday.");
    } catch { setAddError("Unable to create holiday."); } finally { setAddLoading(false); }
  }

  async function toggleActive(holiday: Holiday) {
    await fetch(`/api/holidays/${holiday._id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ isActive: !holiday.isActive }) });
    fetchHolidays();
  }

  async function handleDelete(holidayId: string) {
    if (!confirm("Delete this holiday?")) return;
    await fetch(`/api/holidays/${holidayId}`, { method: "DELETE" });
    fetchHolidays();
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-indigo-600" />
        <p className="mt-3 text-sm text-slate-500">Loading holidays...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Holidays</h1>
          <p className="mt-0.5 text-sm text-slate-500">Manage non-working days for SLA calculation</p>
        </div>
        <Button onClick={() => setShowAdd(true)}>+ Add Holiday</Button>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                {["Date", "Name", "Status", "Actions"].map((h) => (
                  <th key={h} className={`px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-slate-500 ${h === "Actions" ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {holidays.length === 0 ? (
                <tr><td colSpan={4} className="px-5 py-12 text-center text-sm text-slate-500">No holidays configured yet.</td></tr>
              ) : (
                holidays.map((h) => (
                  <tr key={h._id} className="transition-colors hover:bg-slate-50/50">
                    <td className="px-5 py-3.5 font-medium text-slate-900">{formatDateOnly(h.date)}</td>
                    <td className="px-5 py-3.5">{h.name}</td>
                    <td className="px-5 py-3.5"><Badge variant={h.isActive ? "success" : "neutral"}>{h.isActive ? "Active" : "Inactive"}</Badge></td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-2">
                        <Button size="sm" variant="ghost" onClick={() => toggleActive(h)}>{h.isActive ? "Deactivate" : "Activate"}</Button>
                        <Button size="sm" variant="danger" onClick={() => handleDelete(h._id)}>Delete</Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Holiday">
        <div className="space-y-4">
          <Input label="Holiday Name" placeholder="e.g., Independence Day" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <Input label="Date" type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} />
          {addError && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{addError}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button onClick={handleAdd} loading={addLoading} disabled={!newName || !newDate}>Add Holiday</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}