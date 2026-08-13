"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { RawImportUpload } from "@/components/raw-import/raw-import-upload";
import { RawLocationSuggestionCard } from "@/components/raw-import/raw-location-suggestion-card";
import { RawWarehouseSuggestionCard } from "@/components/raw-import/raw-warehouse-suggestion-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { RawImportBatch, RawLocationSuggestion, RawWarehouseSuggestion, Warehouse } from "@/lib/types";

export default function RawImportPage() {
  const [batches, setBatches] = useState<RawImportBatch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  const [whStatusFilter, setWhStatusFilter] = useState("pending");
  const [warehouseSuggestions, setWarehouseSuggestions] = useState<RawWarehouseSuggestion[] | null>(null);
  const [whError, setWhError] = useState<string | null>(null);

  const [locStatusFilter, setLocStatusFilter] = useState("pending");
  const [locationSuggestions, setLocationSuggestions] = useState<RawLocationSuggestion[] | null>(null);
  const [locError, setLocError] = useState<string | null>(null);
  const [warehouseTypeById, setWarehouseTypeById] = useState<Record<string, string>>({});
  const [isGeneratingLocations, setIsGeneratingLocations] = useState(false);
  const fetchedWarehouseIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    (async () => {
      const data = await apiJson<RawImportBatch[]>("/raw-import/batches");
      setBatches(data);
      setSelectedBatchId((prev) => prev || data[0]?.id || "");
    })();
  }, [reloadToken]);

  useEffect(() => {
    if (!selectedBatchId) return;
    (async () => {
      try {
        const query = whStatusFilter ? `?status=${whStatusFilter}` : "";
        const data = await apiJson<RawWarehouseSuggestion[]>(
          `/raw-import/batches/${selectedBatchId}/warehouses${query}`,
        );
        setWarehouseSuggestions(data);
      } catch (err) {
        setWhError(err instanceof ApiError ? err.message : "Could not load warehouse suggestions.");
      }
    })();
  }, [selectedBatchId, whStatusFilter, reloadToken]);

  useEffect(() => {
    if (!selectedBatchId) return;
    (async () => {
      try {
        const query = locStatusFilter ? `?status=${locStatusFilter}` : "";
        const data = await apiJson<RawLocationSuggestion[]>(
          `/raw-import/batches/${selectedBatchId}/locations${query}`,
        );
        setLocationSuggestions(data);
      } catch (err) {
        setLocError(err instanceof ApiError ? err.message : "Could not load location suggestions.");
      }
    })();
  }, [selectedBatchId, locStatusFilter, reloadToken]);

  useEffect(() => {
    if (!locationSuggestions || locationSuggestions.length === 0) return;
    const uniqueIds = Array.from(new Set(locationSuggestions.map((s) => s.warehouse_id))).filter(
      (id) => !fetchedWarehouseIds.current.has(id),
    );
    if (uniqueIds.length === 0) return;
    uniqueIds.forEach((id) => fetchedWarehouseIds.current.add(id));
    (async () => {
      const entries = await Promise.all(
        uniqueIds.map(async (id) => [id, (await apiJson<Warehouse>(`/warehouses/${id}`)).warehouse_type_code] as const),
      );
      setWarehouseTypeById((prev) => ({ ...prev, ...Object.fromEntries(entries) }));
    })();
  }, [locationSuggestions]);

  async function generateLocationSuggestions() {
    if (!selectedBatchId) return;
    setIsGeneratingLocations(true);
    setLocError(null);
    try {
      await apiJson(`/raw-import/batches/${selectedBatchId}/locations/suggest`, { method: "POST" });
      setReloadToken((t) => t + 1);
    } catch (err) {
      setLocError(err instanceof ApiError ? err.message : "Could not generate location suggestions.");
    } finally {
      setIsGeneratingLocations(false);
    }
  }

  const approvedWarehouseCount = warehouseSuggestions?.filter((s) => s.status === "approved").length ?? 0;

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Raw Import</h1>
          <p className="mt-0.5 text-sm text-ink-dim">
            AI-assisted mapping from legacy raw exports to the app&rsquo;s coding scheme — every suggestion needs your
            review before anything is created.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Upload Raw File</CardTitle>
          </CardHeader>
          <CardContent>
            <RawImportUpload
              onUploaded={(batch) => {
                setBatches((prev) => [batch, ...prev]);
                setSelectedBatchId(batch.id);
                setWhStatusFilter("pending");
                setLocStatusFilter("pending");
              }}
            />
          </CardContent>
        </Card>

        {batches.length > 0 && (
          <div className="max-w-md">
            <label className="mb-1 block text-xs font-medium text-ink-dim">Batch</label>
            <Select value={selectedBatchId} onChange={(e) => setSelectedBatchId(e.target.value)}>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.file_name} — {new Date(b.uploaded_at).toLocaleString()}
                </option>
              ))}
            </Select>
          </div>
        )}

        {selectedBatchId && (
          <>
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
                  Warehouse Suggestions
                </h2>
                <div className="w-40">
                  <Select value={whStatusFilter} onChange={(e) => setWhStatusFilter(e.target.value)}>
                    <option value="">All statuses</option>
                    <option value="pending">Pending</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </Select>
                </div>
              </div>

              {whError && <p className="text-sm text-status-critical">{whError}</p>}
              {!whError && warehouseSuggestions === null && <p className="text-sm text-ink-dim">Loading…</p>}
              {warehouseSuggestions !== null && warehouseSuggestions.length === 0 && (
                <p className="text-sm text-ink-dim">No {whStatusFilter || ""} warehouse suggestions.</p>
              )}
              <div className="space-y-3">
                {warehouseSuggestions?.map((s) => (
                  <RawWarehouseSuggestionCard key={s.id} suggestion={s} onChanged={() => setReloadToken((t) => t + 1)} />
                ))}
              </div>
            </div>

            <div className="space-y-3 border-t border-line pt-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
                  Location Suggestions
                </h2>
                <div className="flex items-center gap-3">
                  <Button
                    variant="secondary"
                    disabled={isGeneratingLocations || approvedWarehouseCount === 0}
                    onClick={generateLocationSuggestions}
                  >
                    <Sparkles className="h-4 w-4" />
                    {isGeneratingLocations ? "Asking AI…" : "Generate for approved warehouses"}
                  </Button>
                  <div className="w-40">
                    <Select value={locStatusFilter} onChange={(e) => setLocStatusFilter(e.target.value)}>
                      <option value="">All statuses</option>
                      <option value="pending">Pending</option>
                      <option value="approved">Approved</option>
                      <option value="rejected">Rejected</option>
                    </Select>
                  </div>
                </div>
              </div>
              {approvedWarehouseCount === 0 && (
                <p className="text-sm text-ink-dim">Approve at least one warehouse suggestion above first.</p>
              )}

              {locError && <p className="text-sm text-status-critical">{locError}</p>}
              {!locError && locationSuggestions === null && <p className="text-sm text-ink-dim">Loading…</p>}
              {locationSuggestions !== null && locationSuggestions.length === 0 && approvedWarehouseCount > 0 && (
                <p className="text-sm text-ink-dim">
                  No {locStatusFilter || ""} location suggestions yet — click &ldquo;Generate&rdquo; above.
                </p>
              )}
              <div className="space-y-3">
                {locationSuggestions?.map((s) => (
                  <RawLocationSuggestionCard
                    key={s.id}
                    suggestion={s}
                    warehouseTypeCode={warehouseTypeById[s.warehouse_id]}
                    onChanged={() => setReloadToken((t) => t + 1)}
                  />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
