"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, X } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiJson, ApiError } from "@/lib/api-client";
import type { MergeSuggestion } from "@/lib/types";

export default function MergeSuggestionsPage() {
  const [suggestions, setSuggestions] = useState<MergeSuggestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await apiJson<MergeSuggestion[]>("/merge-suggestions?status=pending");
      setSuggestions(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load merge suggestions.");
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiJson<MergeSuggestion[]>("/merge-suggestions?status=pending");
        setSuggestions(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load merge suggestions.");
      }
    })();
  }, []);

  async function handleApprove(id: string) {
    setBusyId(id);
    try {
      await apiJson(`/merge-suggestions/${id}/approve`, { method: "POST" });
      setSuggestions((prev) => prev?.filter((s) => s.id !== id) ?? null);
    } catch {
      // leave it in the list; the user can retry
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id: string) {
    setBusyId(id);
    try {
      await apiJson(`/merge-suggestions/${id}/reject`, { method: "POST" });
      setSuggestions((prev) => prev?.filter((s) => s.id !== id) ?? null);
    } catch {
      // leave it in the list; the user can retry
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Merge Suggestions</h1>
          <p className="mt-0.5 text-sm text-ink-dim">
            Locations flagged as possible duplicates during upload. Nothing merges automatically — approve confirms
            it&rsquo;s the same place (no new location is created); reject creates it as a genuinely new location.
          </p>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}
        {!error && suggestions === null && <p className="text-sm text-ink-dim">Loading…</p>}
        {suggestions !== null && suggestions.length === 0 && (
          <p className="text-sm text-ink-dim">No pending suggestions right now.</p>
        )}

        <div className="space-y-3">
          {suggestions?.map((s) => (
            <Card key={s.id}>
              <CardContent className="pt-5">
                <p className="text-sm font-medium text-ink">&ldquo;{s.raw_description}&rdquo;</p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-dim">{s.reasoning}</p>
                <div className="mt-3 flex gap-2">
                  <Button variant="secondary" disabled={busyId === s.id} onClick={() => handleApprove(s.id)}>
                    <Check className="h-4 w-4" />
                    Approve (same place)
                  </Button>
                  <Button variant="danger" disabled={busyId === s.id} onClick={() => handleReject(s.id)}>
                    <X className="h-4 w-4" />
                    Reject (different place)
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
