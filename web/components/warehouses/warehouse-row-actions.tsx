"use client";

import { useState } from "react";
import { Pencil, SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Warehouse } from "@/lib/types";

/** Admin's direct-edit form (PATCH /warehouses/{id}) -- name/description/
 * capacity/is_active, never the formula-driving fields. */
export function WarehouseEditForm({ warehouse, onDone }: { warehouse: Warehouse; onDone: () => void }) {
  const [name, setName] = useState(warehouse.name);
  const [description, setDescription] = useState(warehouse.description ?? "");
  const [capacity, setCapacity] = useState(warehouse.capacity?.toString() ?? "");
  const [isActive, setIsActive] = useState(warehouse.is_active ? "true" : "false");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/warehouses/${warehouse.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          description: description || null,
          capacity: capacity === "" ? null : Number(capacity),
          is_active: isActive === "true",
        }),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save changes.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-line bg-paper/60 p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Capacity</label>
          <Input type="number" min={0} value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Status</label>
          <Select value={isActive} onChange={(e) => setIsActive(e.target.value)}>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </Select>
        </div>
      </div>
      {error && <p className="text-sm text-status-critical">{error}</p>}
      <div className="flex gap-2">
        <Button disabled={busy || !name} onClick={handleSubmit}>
          {busy ? "Saving…" : "Save"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

/** PIC's revision-request form (POST /revisions) -- same descriptive-field
 * scope, minus is_active, plus the required comment. Only fields the PIC
 * actually changed are sent, so the eventual diff view in the Review Queue
 * only shows what's genuinely being proposed. */
export function WarehouseRevisionForm({ warehouse, onDone }: { warehouse: Warehouse; onDone: () => void }) {
  const [name, setName] = useState(warehouse.name);
  const [description, setDescription] = useState(warehouse.description ?? "");
  const [capacity, setCapacity] = useState(warehouse.capacity?.toString() ?? "");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const proposedValue: Record<string, string | number | null> = {};
  if (name !== warehouse.name) proposedValue.name = name;
  if ((description || null) !== warehouse.description) proposedValue.description = description || null;
  const capacityValue = capacity === "" ? null : Number(capacity);
  if (capacityValue !== warehouse.capacity) proposedValue.capacity = capacityValue;
  const hasChanges = Object.keys(proposedValue).length > 0;

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await apiJson("/revisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_type: "warehouse", entity_id: warehouse.id, proposed_value: proposedValue, comment }),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit revision.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-line bg-paper/60 p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Capacity</label>
          <Input type="number" min={0} value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-ink-dim">Comment (required)</label>
          <Input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Why is this change needed?" />
        </div>
      </div>
      {error && <p className="text-sm text-status-critical">{error}</p>}
      <div className="flex gap-2">
        <Button disabled={busy || !hasChanges || !comment.trim()} onClick={handleSubmit}>
          <SendHorizonal className="h-4 w-4" />
          {busy ? "Submitting…" : "Submit for Review"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

/** Admin-only: merges this Warehouse into an existing one -- every
 * Location moves over (recoded under the target), then this warehouse is
 * deleted and stops showing up in the list. Only warehouses in the same
 * Hospital Unit are offered as a target, matching the backend's own
 * cross-site guard. */
export function WarehouseMergeForm({
  warehouse,
  warehouses,
  onDone,
}: {
  warehouse: Warehouse;
  warehouses: Warehouse[];
  onDone: () => void;
}) {
  const candidates = warehouses.filter((w) => w.id !== warehouse.id && w.site_id === warehouse.site_id);
  const [targetId, setTargetId] = useState(candidates[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    const target = candidates.find((w) => w.id === targetId);
    if (
      !target ||
      !window.confirm(
        `Merge "${warehouse.generated_code}" (${warehouse.name}) into "${target.generated_code}" (${target.name})? ` +
          `Every Location in ${warehouse.generated_code} will move into ${target.generated_code}, then ` +
          `${warehouse.generated_code} will be deleted. This cannot be undone.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/warehouses/${warehouse.id}/merge-into`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_warehouse_id: targetId }),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not merge this warehouse.");
    } finally {
      setBusy(false);
    }
  }

  if (candidates.length === 0) {
    return (
      <div className="space-y-3 rounded-md border border-line bg-paper/60 p-3">
        <p className="text-sm text-ink-dim">No other warehouse in this Hospital Unit to merge into.</p>
        <Button variant="ghost" onClick={onDone}>
          Close
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-md border border-line bg-paper/60 p-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-ink-dim">Merge Into Warehouse</label>
        <Select value={targetId} onChange={(e) => setTargetId(e.target.value)}>
          {candidates.map((w) => (
            <option key={w.id} value={w.id}>
              {w.generated_code} — {w.name}
            </option>
          ))}
        </Select>
      </div>
      <p className="text-xs text-ink-dim">
        Every Location in this warehouse moves into the target (codes recomputed automatically), then this warehouse
        is deleted.
      </p>
      {error && <p className="text-sm text-status-critical">{error}</p>}
      <div className="flex gap-2">
        <Button disabled={busy || !targetId} onClick={handleSubmit}>
          {busy ? "Merging…" : "Merge Warehouse"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function WarehouseRowActionsTrigger({
  isAdmin,
  hasPendingRevision,
  onEdit,
  onRequestRevision,
}: {
  isAdmin: boolean;
  hasPendingRevision: boolean;
  onEdit: () => void;
  onRequestRevision: () => void;
}) {
  if (isAdmin) {
    return (
      <Button variant="ghost" onClick={onEdit}>
        <Pencil className="h-4 w-4" />
        Edit
      </Button>
    );
  }
  return (
    <Button variant="ghost" disabled={hasPendingRevision} onClick={onRequestRevision}>
      <SendHorizonal className="h-4 w-4" />
      {hasPendingRevision ? "Revision Pending" : "Request Revision"}
    </Button>
  );
}
