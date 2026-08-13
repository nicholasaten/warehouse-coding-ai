"use client";

import { useState } from "react";
import { ArrowRightLeft, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Location, Warehouse } from "@/lib/types";
import {
  LocationEditForm,
  LocationReassignWarehouseForm,
  LocationRevisionForm,
  LocationRowActionsTrigger,
} from "./location-row-actions";

function LocationRow({
  location,
  warehouseLabel,
  warehouses,
  isAdmin,
  onChanged,
}: {
  location: Location;
  warehouseLabel: string;
  warehouses: Warehouse[];
  isAdmin: boolean;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"edit" | "request" | "reassign" | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleDelete() {
    if (!window.confirm(`Delete location "${location.generated_code}" (${location.description})? This cannot be undone.`)) {
      return;
    }
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await apiJson(`/locations/${location.id}`, { method: "DELETE" });
      onChanged();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not delete this location.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <TR>
        <TD className="font-mono text-xs">{location.generated_code}</TD>
        <TD>{warehouseLabel}</TD>
        <TD>{location.description}</TD>
        <TD className="text-ink-dim">{location.category_rack_raw ?? "—"}</TD>
        <TD>
          <div className="flex flex-wrap items-center gap-1.5">
            {!location.is_active && <Badge tone="neutral" label="Inactive" />}
            {location.has_pending_revision && <Badge tone="warning" label="Revision Pending" />}
          </div>
        </TD>
        <TD>
          <div className="flex flex-wrap items-center gap-1">
            <LocationRowActionsTrigger
              isAdmin={isAdmin}
              hasPendingRevision={location.has_pending_revision}
              onEdit={() => setMode("edit")}
              onRequestRevision={() => setMode("request")}
            />
            {isAdmin && (
              <Button variant="ghost" disabled={isDeleting} onClick={() => setMode("reassign")}>
                <ArrowRightLeft className="h-4 w-4" />
                Move
              </Button>
            )}
            {isAdmin && (
              <Button variant="ghost" disabled={isDeleting} onClick={handleDelete}>
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            )}
          </div>
          {deleteError && <p className="mt-1 text-xs text-status-critical">{deleteError}</p>}
        </TD>
      </TR>
      {mode && (
        <TR>
          <TD colSpan={6}>
            {mode === "edit" ? (
              <LocationEditForm
                location={location}
                onDone={() => {
                  setMode(null);
                  onChanged();
                }}
              />
            ) : mode === "reassign" ? (
              <LocationReassignWarehouseForm
                location={location}
                warehouses={warehouses}
                onDone={() => {
                  setMode(null);
                  onChanged();
                }}
              />
            ) : (
              <LocationRevisionForm
                location={location}
                onDone={() => {
                  setMode(null);
                  onChanged();
                }}
              />
            )}
          </TD>
        </TR>
      )}
    </>
  );
}

export function LocationTable({
  locations,
  warehouses,
  warehouseById,
  isAdmin,
  onChanged,
}: {
  locations: Location[];
  warehouses: Warehouse[];
  warehouseById: Record<string, Warehouse>;
  isAdmin: boolean;
  onChanged: () => void;
}) {
  if (locations.length === 0) {
    return <p className="text-sm text-ink-dim">No locations yet.</p>;
  }

  return (
    <Table>
      <THead>
        <TR>
          <TH>Generated Code</TH>
          <TH>Warehouse</TH>
          <TH>Description</TH>
          <TH>Category Rack</TH>
          <TH>Status</TH>
          <TH>Actions</TH>
        </TR>
      </THead>
      <TBody>
        {locations.map((l) => (
          <LocationRow
            key={l.id}
            location={l}
            warehouseLabel={warehouseById[l.warehouse_id]?.generated_code ?? "—"}
            warehouses={warehouses}
            isAdmin={isAdmin}
            onChanged={onChanged}
          />
        ))}
      </TBody>
    </Table>
  );
}
