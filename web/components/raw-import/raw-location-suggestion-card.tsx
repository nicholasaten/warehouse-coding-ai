"use client";

import { useEffect, useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { CategoryRackMapping, RawLocationSuggestion } from "@/lib/types";

const STATUS_TONE: Record<RawLocationSuggestion["status"], "warning" | "good" | "critical"> = {
  pending: "warning",
  approved: "good",
  rejected: "critical",
};

export function RawLocationSuggestionCard({
  suggestion,
  warehouseTypeCode,
  onChanged,
}: {
  suggestion: RawLocationSuggestion;
  warehouseTypeCode: string | undefined;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"override" | null>(null);
  const [options, setOptions] = useState<string[]>([]);
  const [categoryRack, setCategoryRack] = useState(suggestion.suggested_category_rack ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "override" || !warehouseTypeCode) return;
    apiJson<CategoryRackMapping[]>("/config/category-rack-mappings").then((data) => {
      const values = Array.from(
        new Set(data.filter((m) => m.warehouse_type_code === warehouseTypeCode).map((m) => m.raw_category_text)),
      ).sort();
      setOptions(values);
      setCategoryRack((prev) => prev || values[0] || "");
    });
  }, [mode, warehouseTypeCode]);

  async function approve(withOverride: boolean) {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/raw-import/locations/${suggestion.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(withOverride ? { category_rack: categoryRack } : {}),
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
      await apiJson(`/raw-import/locations/${suggestion.id}/reject`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject.");
    } finally {
      setBusy(false);
    }
  }

  const hasSuggestion = !!suggestion.suggested_category_rack;

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <p className="text-sm font-medium text-ink">{suggestion.legacy_description}</p>
            <p className="text-xs text-ink-dim">
              Legacy code {suggestion.legacy_code ?? "—"}
              {!suggestion.is_active_raw && " · marked inactive in the raw file"}
            </p>
          </div>
          <Badge tone={STATUS_TONE[suggestion.status]} label={suggestion.status} />
        </div>

        <div className="mt-3 rounded-md border border-line bg-paper/60 p-3 text-sm">
          {hasSuggestion ? (
            <p>
              AI suggests <span className="font-mono font-medium text-ink">{suggestion.suggested_category_rack}</span>
              {suggestion.reasoning && <span className="text-ink-dim"> — {suggestion.reasoning}</span>}
            </p>
          ) : (
            <p className="text-status-warning">
              No confident AI suggestion{suggestion.reasoning ? ` (${suggestion.reasoning})` : ""} — assign manually.
            </p>
          )}
        </div>

        {suggestion.status === "approved" && suggestion.created_merge_suggestion_id && (
          <p className="mt-2 text-xs text-status-warning">
            Similar to an existing location — held as a Merge Suggestion for review instead of a new Location.
          </p>
        )}

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
                <div className="max-w-xs">
                  <label className="mb-1 block text-xs font-medium text-ink-dim">Category Rack</label>
                  <Select value={categoryRack} onChange={(e) => setCategoryRack(e.target.value)}>
                    {options.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="flex gap-2">
                  <Button disabled={busy || !categoryRack} onClick={() => approve(true)}>
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
