"use client";

import { useEffect, useState } from "react";

import { StatTile } from "@/components/ui/stat-tile";
import { LocationTable } from "@/components/warehouses/location-table";
import { WarehouseTable } from "@/components/warehouses/warehouse-table";
import { apiJson, ApiError } from "@/lib/api-client";
import type { DashboardSummary, Location, Warehouse } from "@/lib/types";

/** The reverse direction of the Revision workflow: whenever the admin
 * creates or edits a Warehouse/Location in this PIC's Hospital Unit, it
 * shows up here until the PIC explicitly confirms they've reviewed the
 * current coding and agree with it ("Accept"). */
export function PicDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [pendingWarehouses, setPendingWarehouses] = useState<Warehouse[] | null>(null);
  const [pendingLocations, setPendingLocations] = useState<Location[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    apiJson<DashboardSummary>("/dashboard/pic-summary")
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load the dashboard."));
  }, [reloadToken]);

  useEffect(() => {
    apiJson<Warehouse[]>("/warehouses").then(setWarehouses).catch(() => {});
  }, [reloadToken]);

  useEffect(() => {
    apiJson<Warehouse[]>("/warehouses?has_pending_pic_review=true").then(setPendingWarehouses).catch(() => {});
  }, [reloadToken]);

  useEffect(() => {
    apiJson<Location[]>("/locations?has_pending_pic_review=true").then(setPendingLocations).catch(() => {});
  }, [reloadToken]);

  const warehouseById = Object.fromEntries(warehouses.map((w) => [w.id, w]));
  const onChanged = () => setReloadToken((t) => t + 1);
  const nothingPending = pendingWarehouses?.length === 0 && pendingLocations?.length === 0;

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-status-critical">{error}</p>}

      <section>
        <h2 className="mb-2 font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
          Needs Your Review
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <StatTile
            label="Warehouses to Accept"
            value={pendingWarehouses?.length ?? "…"}
            tone={pendingWarehouses && pendingWarehouses.length > 0 ? "warning" : "good"}
          />
          <StatTile
            label="Locations to Accept"
            value={pendingLocations?.length ?? "…"}
            tone={pendingLocations && pendingLocations.length > 0 ? "warning" : "good"}
          />
        </div>
      </section>

      {nothingPending && (
        <p className="text-sm text-ink-dim">Nothing needs your review right now — you&apos;re all caught up.</p>
      )}

      {pendingWarehouses && pendingWarehouses.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-sm font-medium text-ink">Warehouses Awaiting Your Review</h3>
          <WarehouseTable warehouses={pendingWarehouses} isAdmin={false} sites={[]} onChanged={onChanged} />
        </section>
      )}

      {pendingLocations && pendingLocations.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-sm font-medium text-ink">Locations Awaiting Your Review</h3>
          <LocationTable
            locations={pendingLocations}
            warehouses={warehouses}
            warehouseById={warehouseById}
            isAdmin={false}
            onChanged={onChanged}
          />
        </section>
      )}

      {summary && (
        <section>
          <h2 className="mb-2 font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
            Your Hospital Unit
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <StatTile label="Total Warehouses" value={summary.warehouses.total_warehouses} />
            <StatTile label="Active" value={summary.warehouses.active_warehouses} tone="good" />
            <StatTile label="Empty" value={summary.warehouses.empty_warehouses} />
            <StatTile label="Underutilized" value={summary.warehouses.underutilized_warehouses} tone="warning" />
            <StatTile label="Overloaded" value={summary.warehouses.overloaded_warehouses} tone="critical" />
            <StatTile label="No Capacity Set" value={summary.warehouses.warehouses_without_capacity_set} />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile label="Total Locations" value={summary.locations.total_locations} />
            <StatTile
              label="Pending Duplicate Review"
              value={summary.locations.pending_duplicate_review}
              tone={summary.locations.pending_duplicate_review > 0 ? "warning" : "default"}
            />
          </div>
        </section>
      )}
    </div>
  );
}
