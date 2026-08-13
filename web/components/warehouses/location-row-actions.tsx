"use client";

import { useState } from "react";
import { Pencil, SendHorizonal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Location, Warehouse } from "@/lib/types";

/** Admin's direct-edit form (PATCH /locations/{id}) -- description/
 * category_rack_raw/is_active, never the formula-driving fields. */
export function LocationEditForm({ location, onDone }: { location: Location; onDone: () => void }) {
  const [description, setDescription] = useState(location.description);
  const [categoryRack, setCategoryRack] = useState(location.category_rack_raw ?? "");
  const [isActive, setIsActive] = useState(location.is_active ? "true" : "false");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/locations/${location.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description,
          category_rack_raw: categoryRack || null,
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
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Category Rack</label>
          <Input value={categoryRack} onChange={(e) => setCategoryRack(e.target.value)} />
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
        <Button disabled={busy || !description} onClick={handleSubmit}>
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
 * actually changed are sent. */
export function LocationRevisionForm({ location, onDone }: { location: Location; onDone: () => void }) {
  const [description, setDescription] = useState(location.description);
  const [categoryRack, setCategoryRack] = useState(location.category_rack_raw ?? "");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const proposedValue: Record<string, string | null> = {};
  if (description !== location.description) proposedValue.description = description;
  if ((categoryRack || null) !== location.category_rack_raw) proposedValue.category_rack_raw = categoryRack || null;
  const hasChanges = Object.keys(proposedValue).length > 0;

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await apiJson("/revisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entity_type: "location", entity_id: location.id, proposed_value: proposedValue, comment }),
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
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Category Rack</label>
          <Input value={categoryRack} onChange={(e) => setCategoryRack(e.target.value)} />
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

/** Admin-only: moves a Location into a different Warehouse without
 * deleting/recreating it -- e.g. when combining two warehouses into one.
 * The code/sequence are recomputed server-side under the target warehouse,
 * never edited directly here. */
export function LocationReassignWarehouseForm({
  location,
  warehouses,
  onDone,
}: {
  location: Location;
  warehouses: Warehouse[];
  onDone: () => void;
}) {
  const candidates = warehouses.filter((w) => w.id !== location.warehouse_id);
  const [warehouseId, setWarehouseId] = useState(candidates[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/locations/${location.id}/reassign-warehouse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ warehouse_id: warehouseId }),
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reassign this location.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-md border border-line bg-paper/60 p-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-ink-dim">Move to Warehouse</label>
        <Select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
          {candidates.map((w) => (
            <option key={w.id} value={w.id}>
              {w.generated_code} — {w.name}
            </option>
          ))}
        </Select>
      </div>
      <p className="text-xs text-ink-dim">
        The generated code and sequence number are recomputed automatically under the target warehouse.
      </p>
      {error && <p className="text-sm text-status-critical">{error}</p>}
      <div className="flex gap-2">
        <Button disabled={busy || !warehouseId} onClick={handleSubmit}>
          {busy ? "Moving…" : "Move Location"}
        </Button>
        <Button variant="ghost" disabled={busy} onClick={onDone}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

export function LocationRowActionsTrigger({
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
