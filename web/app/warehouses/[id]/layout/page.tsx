"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { LayoutCanvas } from "@/components/warehouses/layout-canvas";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Location, Warehouse } from "@/lib/types";

export default function WarehouseLayoutPage() {
  const params = useParams<{ id: string }>();
  const warehouseId = params.id;

  const [warehouse, setWarehouse] = useState<Warehouse | null>(null);
  const [locations, setLocations] = useState<Location[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [wh, locs] = await Promise.all([
          apiJson<Warehouse>(`/warehouses/${warehouseId}`),
          apiJson<Location[]>(`/locations?warehouse_id=${warehouseId}`),
        ]);
        setWarehouse(wh);
        setLocations(locs);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load this warehouse's layout.");
      }
    })();
  }, [warehouseId]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <Link href="/warehouses" className="inline-flex items-center gap-1 text-sm text-ink-dim hover:text-ink">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Warehouses
          </Link>
          <h1 className="mt-2 text-xl font-semibold text-ink">
            {warehouse ? `${warehouse.generated_code} — ${warehouse.name}` : "Warehouse Layout"}
          </h1>
          <p className="mt-0.5 text-sm text-ink-dim">
            Lay out this warehouse&apos;s Locations visually. Position and size are free-form and don&apos;t affect
            the generated code.
          </p>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}
        {!error && locations === null && <p className="text-sm text-ink-dim">Loading…</p>}
        {locations !== null && <LayoutCanvas locations={locations} />}
      </div>
    </AppShell>
  );
}
