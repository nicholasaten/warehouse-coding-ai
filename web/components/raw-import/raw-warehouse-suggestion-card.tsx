"use client";

import { useEffect, useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { RawWarehouseSuggestion, WarehouseCodeConfig, WarehouseTypeConfig } from "@/lib/types";

const STATUS_TONE: Record<RawWarehouseSuggestion["status"], "warning" | "good" | "critical"> = {
  pending: "warning",
  approved: "good",
  rejected: "critical",
};

export function RawWarehouseSuggestionCard({
  suggestion,
  onChanged,
}: {
  suggestion: RawWarehouseSuggestion;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"override" | null>(null);
  const [types, setTypes] = useState<WarehouseTypeConfig[]>([]);
  const [codes, setCodes] = useState<WarehouseCodeConfig[]>([]);
  const [typeCode, setTypeCode] = useState(suggestion.suggested_warehouse_type_code ?? "");
  const [code, setCode] = useState(suggestion.suggested_warehouse_code ?? "");
  const [name, setName] = useState(suggestion.legacy_name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "override") return;
    apiJson<WarehouseTypeConfig[]>("/config/warehouse-types").then((data) => {
      setTypes(data);
      setTypeCode((prev) => prev || data[0]?.code || "");
    });
  }, [mode]);

  useEffect(() => {
    if (!typeCode) return;
    apiJson<WarehouseCodeConfig[]>(`/config/warehouse-codes?warehouse_type_code=${encodeURIComponent(typeCode)}`).then(
      (data) => {
        setCodes(data);
        setCode((prev) => prev || data[0]?.code || "");
      },
    );
  }, [typeCode]);

  async function approve(withOverride: boolean) {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/raw-import/warehouses/${suggestion.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          withOverride ? { warehouse_type_code: typeCode, warehouse_code: code, name } : {},
        ),
      });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve.");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/raw-import/warehouses/${suggestion.id}/reject`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject.");
    } finally {
      setBusy(false);
    }
  }

  const hasSuggestion = !!suggestion.suggested_warehouse_type_code;

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-ink">{suggestion.legacy_name}</p>
            <p className="text-xs text-ink-dim">
              Legacy code {suggestion.legacy_code} · {suggestion.raw_rows.length} rack row
              {suggestion.raw_rows.length === 1 ? "" : "s"}
            </p>
          </div>
          <Badge tone={STATUS_TONE[suggestion.status]} label={suggestion.status} />
        </div>

        {suggestion.consolidated_legacy_names.length > 0 && (
          <p className="mt-2 text-xs text-status-warning">
            Also covers: {suggestion.consolidated_legacy_names.join(", ")} — the AI judged these to be the same
            physical warehouse under a different billing/status label. Double-check before approving; rejecting
            discards all of them together.
          </p>
        )}

        <div className="mt-3 rounded-md border border-line bg-paper/60 p-3 text-sm">
          {hasSuggestion ? (
            <p>
              AI suggests <span className="font-mono font-medium text-ink">{suggestion.suggested_warehouse_type_code}/{suggestion.suggested_warehouse_code}</span>
              {suggestion.reasoning && <span className="text-ink-dim"> — {suggestion.reasoning}</span>}
            </p>
          ) : (
            <p className="text-status-warning">
              No confident AI suggestion{suggestion.reasoning ? ` (${suggestion.reasoning})` : ""} — assign manually.
            </p>
          )}
        </div>

        {error && <p className="mt-2 text-sm text-status-critical">{error}</p>}

        {suggestion.status === "pending" && (
          <div className="mt-4">
            {mode === null && (
              <div className="flex flex-wrap gap-2">
                {hasSuggestion && (
                  <Button variant="secondary" disabled={busy} onClick={() => approve(false)}>
                    <Check className="h-4 w-4" />
                    Approve as suggested
                  </Button>
                )}
                <Button variant="secondary" disabled={busy} onClick={() => setMode("override")}>
                  <Pencil className="h-4 w-4" />
                  {hasSuggestion ? "Edit & Approve" : "Assign Manually"}
                </Button>
                <Button variant="danger" disabled={busy} onClick={reject}>
                  <X className="h-4 w-4" />
                  Reject
                </Button>
              </div>
            )}

            {mode === "override" && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
                    <label className="mb-1 block text-xs font-medium text-ink-dim">Warehouse Name</label>
                    <Input value={name} onChange={(e) => setName(e.target.value)} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button disabled={busy || !typeCode || !code || !name} onClick={() => approve(true)}>
                    Confirm & Approve
                  </Button>
                  <Button variant="ghost" disabled={busy} onClick={() => setMode(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
