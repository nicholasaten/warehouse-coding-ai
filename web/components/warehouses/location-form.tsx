"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Location, LocationTypeConfig, Warehouse } from "@/lib/types";

export function LocationForm({ onCreated }: { onCreated: (location: Location) => void }) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [locTypes, setLocTypes] = useState<LocationTypeConfig[]>([]);

  const [warehouseId, setWarehouseId] = useState("");
  const [locTypeCode, setLocTypeCode] = useState("");
  const [categoryRack, setCategoryRack] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const data = await apiJson<Warehouse[]>("/warehouses");
      setWarehouses(data);
      if (data.length > 0) setWarehouseId(data[0].id);
    })();
  }, []);

  const selectedWarehouse = warehouses.find((w) => w.id === warehouseId);

  useEffect(() => {
    if (!selectedWarehouse) return;
    (async () => {
      const data = await apiJson<LocationTypeConfig[]>(
        `/config/location-types?warehouse_type_code=${encodeURIComponent(selectedWarehouse.warehouse_type_code)}`,
      );
      setLocTypes(data);
      setLocTypeCode(data.length > 0 ? data[0].code : "");
    })();
  }, [selectedWarehouse]);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      const location = await apiJson<Location>("/locations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          warehouse_id: warehouseId,
          location_type_code: locTypeCode,
          category_rack_raw: categoryRack || undefined,
          description,
        }),
      });
      onCreated(location);
      setCategoryRack("");
      setDescription("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create location.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Warehouse</label>
          <Select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.generated_code} — {w.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Location Type</label>
          <Select value={locTypeCode} onChange={(e) => setLocTypeCode(e.target.value)}>
            {locTypes.map((t) => (
              <option key={t.code} value={t.code}>
                {t.code} — {t.description}
                {t.is_whole_warehouse ? " (whole warehouse)" : ""}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Category Rack (optional)</label>
          <Input value={categoryRack} onChange={(e) => setCategoryRack(e.target.value)} placeholder="e.g. DRUGS" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. DRUGS - TABLET" />
        </div>
      </div>

      {error && <p className="text-sm text-status-critical">{error}</p>}

      <Button onClick={handleSubmit} disabled={isSubmitting || !warehouseId || !locTypeCode || !description}>
        {isSubmitting ? "Creating…" : "Create Location"}
      </Button>
    </div>
  );
}
