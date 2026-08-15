"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, GitMerge, LayoutGrid, Trash2 } from "lucide-react";

import { Badge, OccupancyBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Site, Warehouse, WarehouseCapacity } from "@/lib/types";
import {
  WarehouseEditForm,
  WarehouseMergeForm,
  WarehouseRevisionForm,
  WarehouseRowActionsTrigger,
} from "./warehouse-row-actions";

function WarehouseRow({
  warehouse,
  warehouses,
  capacity,
  siteLabel,
  isAdmin,
  onChanged,
}: {
  warehouse: Warehouse;
  warehouses: Warehouse[];
  capacity?: WarehouseCapacity;
  siteLabel?: string;
  isAdmin: boolean;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"edit" | "request" | "merge" | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [ackError, setAckError] = useState<string | null>(null);
  const [isAcknowledging, setIsAcknowledging] = useState(false);

  async function handleAcknowledge() {
    setIsAcknowledging(true);
    setAckError(null);
    try {
      await apiJson(`/warehouses/${warehouse.id}/acknowledge`, { method: "POST" });
      onChanged();
    } catch (err) {
      setAckError(err instanceof ApiError ? err.message : "Could not confirm this warehouse.");
    } finally {
      setIsAcknowledging(false);
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        `Delete warehouse "${warehouse.generated_code}" (${warehouse.name})? This also deletes every Location inside it. This cannot be undone.`,
      )
    ) {
      return;
    }
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await apiJson(`/warehouses/${warehouse.id}`, { method: "DELETE" });
      onChanged();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not delete this warehouse.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <TR>
        <TD className="font-mono text-xs">{warehouse.generated_code}</TD>
        {isAdmin && <TD className="text-ink-dim">{siteLabel ?? "—"}</TD>}
        <TD>{warehouse.name}</TD>
        <TD>{warehouse.warehouse_type_code}</TD>
        <TD className="tabular">{capacity?.location_count ?? "…"}</TD>
        <TD className="tabular">{warehouse.capacity ?? "—"}</TD>
        <TD>{capacity ? <OccupancyBadge status={capacity.status} /> : null}</TD>
        <TD>
          <div className="flex flex-wrap items-center gap-1.5">
            {!warehouse.is_active && <Badge tone="neutral" label="Inactive" />}
            {warehouse.has_pending_revision && <Badge tone="warning" label="Revision Pending" />}
            {warehouse.needs_pic_review ? (
              <Badge tone="warning" label="Awaiting PIC Review" />
            ) : (
              <Badge tone="good" label="PIC Confirmed" />
            )}
          </div>
        </TD>
        <TD>
          <div className="flex flex-wrap items-center gap-1">
            <WarehouseRowActionsTrigger
              isAdmin={isAdmin}
              hasPendingRevision={warehouse.has_pending_revision}
              onEdit={() => setMode("edit")}
              onRequestRevision={() => setMode("request")}
            />
            {!isAdmin && warehouse.needs_pic_review && (
              <Button variant="ghost" disabled={isAcknowledging} onClick={handleAcknowledge}>
                <CheckCircle2 className="h-4 w-4" />
                {isAcknowledging ? "Confirming…" : "Accept"}
              </Button>
            )}
            {isAdmin && (
              <Link
                href={`/warehouses/${warehouse.id}/layout`}
                className="inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-ink-dim transition-colors hover:bg-accent-wash hover:text-ink"
              >
                <LayoutGrid className="h-4 w-4" />
                Layout
              </Link>
            )}
            {isAdmin && (
              <Button variant="ghost" disabled={isDeleting} onClick={() => setMode("merge")}>
                <GitMerge className="h-4 w-4" />
                Merge
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
          {ackError && <p className="mt-1 text-xs text-status-critical">{ackError}</p>}
        </TD>
      </TR>
      {mode && (
        <TR>
          <TD colSpan={isAdmin ? 9 : 8}>
            {mode === "edit" ? (
              <WarehouseEditForm
                warehouse={warehouse}
                onDone={() => {
                  setMode(null);
                  onChanged();
                }}
              />
            ) : mode === "merge" ? (
              <WarehouseMergeForm
                warehouse={warehouse}
                warehouses={warehouses}
                onDone={() => {
                  setMode(null);
                  onChanged();
                }}
              />
            ) : (
              <WarehouseRevisionForm
                warehouse={warehouse}
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

export function WarehouseTable({
  warehouses,
  isAdmin,
  sites,
  onChanged,
}: {
  warehouses: Warehouse[];
  isAdmin: boolean;
  sites: Site[];
  onChanged: () => void;
}) {
  const [capacities, setCapacities] = useState<Record<string, WarehouseCapacity>>({});
  const siteById = Object.fromEntries(sites.map((s) => [s.id, s]));

  useEffect(() => {
    (async () => {
      const entries = await Promise.all(
        warehouses.map(async (w) => [w.id, await apiJson<WarehouseCapacity>(`/warehouses/${w.id}/capacity`)] as const),
      );
      setCapacities(Object.fromEntries(entries));
    })();
  }, [warehouses]);

  if (warehouses.length === 0) {
    return <p className="text-sm text-ink-dim">No warehouses yet.</p>;
  }

  return (
    <Table>
      <THead>
        <TR>
          <TH>Generated Code</TH>
          {isAdmin && <TH>Hospital Code</TH>}
          <TH>Name</TH>
          <TH>Type</TH>
          <TH>Locations</TH>
          <TH>Capacity</TH>
          <TH>Occupancy</TH>
          <TH>Status</TH>
          <TH>Actions</TH>
        </TR>
      </THead>
      <TBody>
        {warehouses.map((w) => (
          <WarehouseRow
            key={w.id}
            warehouse={w}
            warehouses={warehouses}
            capacity={capacities[w.id]}
            siteLabel={siteById[w.site_id]?.code}
            isAdmin={isAdmin}
            onChanged={onChanged}
          />
        ))}
      </TBody>
    </Table>
  );
}
