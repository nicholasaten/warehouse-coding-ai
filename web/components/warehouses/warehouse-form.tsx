"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Site, Warehouse, WarehouseCodeConfig, WarehouseTypeConfig } from "@/lib/types";

export function WarehouseForm({ onCreated }: { onCreated: (warehouse: Warehouse) => void }) {
  const [sites, setSites] = useState<Site[]>([]);
  const [types, setTypes] = useState<WarehouseTypeConfig[]>([]);
  const [codes, setCodes] = useState<WarehouseCodeConfig[]>([]);

  const [siteId, setSiteId] = useState("");
  const [typeCode, setTypeCode] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [capacity, setCapacity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const [siteData, typeData] = await Promise.all([
        apiJson<Site[]>("/config/sites"),
        apiJson<WarehouseTypeConfig[]>("/config/warehouse-types"),
      ]);
      setSites(siteData);
      setTypes(typeData);
      if (siteData.length > 0) setSiteId(siteData[0].id);
      if (typeData.length > 0) setTypeCode(typeData[0].code);
    })();
  }, []);

  useEffect(() => {
    if (!typeCode) return;
    (async () => {
      const codeData = await apiJson<WarehouseCodeConfig[]>(
        `/config/warehouse-codes?warehouse_type_code=${encodeURIComponent(typeCode)}`,
      );
      setCodes(codeData);
      setCode(codeData.length > 0 ? codeData[0].code : "");
    })();
  }, [typeCode]);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      const warehouse = await apiJson<Warehouse>("/warehouses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_id: siteId,
          warehouse_type_code: typeCode,
          warehouse_code: code,
          name,
          description: description || undefined,
          capacity: capacity ? Number(capacity) : undefined,
        }),
      });
      onCreated(warehouse);
      setName("");
      setDescription("");
      setCapacity("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create warehouse.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Site</label>
          <Select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} — {s.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Warehouse Type</label>
          <Select value={typeCode} onChange={(e) => setTypeCode(e.target.value)}>
            {types.map((t) => (
              <option key={t.code} value={t.code}>
                {t.code} — {t.description}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Warehouse Code</label>
          <Select value={code} onChange={(e) => setCode(e.target.value)}>
            {codes.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} — {c.description}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Capacity (optional)</label>
          <Input type="number" min={0} value={capacity} onChange={(e) => setCapacity(e.target.value)} placeholder="e.g. 20" />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-ink-dim">Warehouse Name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Pharmacy Mainstore Drugs" />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs font-medium text-ink-dim">Description (optional)</label>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
      </div>

      {error && <p className="text-sm text-status-critical">{error}</p>}

      <Button onClick={handleSubmit} disabled={isSubmitting || !siteId || !typeCode || !code || !name}>
        {isSubmitting ? "Creating…" : "Create Warehouse"}
      </Button>
    </div>
  );
}
