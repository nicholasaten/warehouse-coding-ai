"use client";

import { useState } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Revision } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  description: "Description",
  capacity: "Capacity",
  category_rack_raw: "Category Rack",
};

const STATUS_TONE: Record<Revision["status"], "warning" | "good" | "critical"> = {
  pending: "warning",
  approved: "good",
  rejected: "critical",
};

function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

type EntityContext = { generated_code: string; label: string };

export function RevisionCard({
  revision,
  isAdmin,
  entityContext,
  submittedByName,
  reviewedByName,
  onChanged,
}: {
  revision: Revision;
  isAdmin: boolean;
  entityContext?: EntityContext;
  submittedByName?: string;
  reviewedByName?: string | null;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"reject" | "edit" | null>(null);
  const [reason, setReason] = useState("");
  const [editValues, setEditValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(revision.proposed_value).map(([field, value]) => [field, value === null ? "" : String(value)])),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fields = Object.keys(revision.proposed_value);

  async function handleApprove() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/revisions/${revision.id}/approve`, { method: "POST" });
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve.");
    } finally {
      setBusy(false);
    }
  }

  async function handleReject() {
    setBusy(true);
    setError(null);
    try {
      await apiJson(`/revisions/${revision.id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      setMode(null);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEditApprove() {
    setBusy(true);
    setError(null);
    try {
      const finalValue: Record<string, string | number | null> = {};
      for (const field of fields) {
        const raw = editValues[field] ?? "";
        finalValue[field] = field === "capacity" ? (raw === "" ? null : Number(raw)) : raw || null;
      }
      await apiJson(`/revisions/${revision.id}/edit-approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ final_value: finalValue }),
      });
      setMode(null);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not edit & approve.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Badge tone="neutral" label={revision.entity_type === "warehouse" ? "Warehouse" : "Location"} />
              <span className="font-mono text-xs text-ink">{entityContext?.generated_code ?? "…"}</span>
              <Badge tone={STATUS_TONE[revision.status]} label={revision.status} />
            </div>
            {entityContext?.label && <p className="mt-1 text-xs text-ink-dim">{entityContext.label}</p>}
          </div>
          <div className="text-right text-xs text-ink-dim">
            {submittedByName && <p>Submitted by {submittedByName}</p>}
            <p>{formatDate(revision.submitted_at)}</p>
          </div>
        </div>

        <p className="mt-3 text-sm italic text-ink-dim">&ldquo;{revision.comment}&rdquo;</p>

        <div className="mt-3 space-y-1.5 rounded-md border border-line bg-paper/60 p-3">
          {fields.map((field) => (
            <div key={field} className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <span className="w-32 flex-none text-xs font-medium uppercase tracking-wide text-ink-dim">
                {FIELD_LABELS[field] ?? field}
              </span>
              <span className="text-ink-dim line-through">{formatValue(revision.original_value[field])}</span>
              <span className="text-ink-dim">→</span>
              <span className="font-medium text-ink">{formatValue(revision.proposed_value[field])}</span>
            </div>
          ))}
        </div>

        {revision.status !== "pending" && (
          <div className="mt-3 space-y-1 text-xs text-ink-dim">
            {reviewedByName && revision.reviewed_at && (
              <p>
                {revision.status === "approved" ? "Approved" : "Rejected"} by {reviewedByName} on{" "}
                {formatDate(revision.reviewed_at)}
              </p>
            )}
            {revision.status === "rejected" && revision.rejection_reason && (
              <p className="text-status-critical">Reason: {revision.rejection_reason}</p>
            )}
            {revision.status === "approved" && revision.final_value && (
              <div className="space-y-0.5">
                <p>Final value applied:</p>
                {fields.map((field) => (
                  <p key={field}>
                    {FIELD_LABELS[field] ?? field}:{" "}
                    <span className="font-medium text-ink">{formatValue(revision.final_value?.[field])}</span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {error && <p className="mt-2 text-sm text-status-critical">{error}</p>}

        {isAdmin && revision.status === "pending" && (
          <div className="mt-4">
            {mode === null && (
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" disabled={busy} onClick={handleApprove}>
                  <Check className="h-4 w-4" />
                  Approve
                </Button>
                <Button variant="secondary" disabled={busy} onClick={() => setMode("edit")}>
                  <Pencil className="h-4 w-4" />
                  Edit &amp; Approve
                </Button>
                <Button variant="danger" disabled={busy} onClick={() => setMode("reject")}>
                  <X className="h-4 w-4" />
                  Reject
                </Button>
              </div>
            )}

            {mode === "reject" && (
              <div className="space-y-2">
                <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for rejecting (required)" />
                <div className="flex gap-2">
                  <Button variant="danger" disabled={busy || !reason.trim()} onClick={handleReject}>
                    Confirm Reject
                  </Button>
                  <Button variant="ghost" disabled={busy} onClick={() => setMode(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {mode === "edit" && (
              <div className="space-y-2">
                {fields.map((field) => (
                  <div key={field}>
                    <label className="mb-1 block text-xs font-medium text-ink-dim">{FIELD_LABELS[field] ?? field}</label>
                    <Input
                      type={field === "capacity" ? "number" : "text"}
                      value={editValues[field] ?? ""}
                      onChange={(e) => setEditValues((prev) => ({ ...prev, [field]: e.target.value }))}
                    />
                  </div>
                ))}
                <div className="flex gap-2">
                  <Button variant="secondary" disabled={busy} onClick={handleEditApprove}>
                    Confirm &amp; Approve
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
