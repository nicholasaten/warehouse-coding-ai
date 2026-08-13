"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { RevisionCard } from "@/components/revisions/revision-card";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { Location, Revision, UserAccount, Warehouse } from "@/lib/types";

type EntityContext = { generated_code: string; label: string };

export default function RevisionsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [revisions, setRevisions] = useState<Revision[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [entityContext, setEntityContext] = useState<Record<string, EntityContext>>({});
  const [userMap, setUserMap] = useState<Record<string, string>>({});

  useEffect(() => {
    (async () => {
      try {
        const query = statusFilter ? `?status=${statusFilter}` : "";
        const data = await apiJson<Revision[]>(`/revisions${query}`);
        setRevisions(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load revisions.");
      }
    })();
  }, [statusFilter, reloadToken]);

  useEffect(() => {
    if (!isAdmin) return;
    apiJson<UserAccount[]>("/users")
      .then((users) => setUserMap(Object.fromEntries(users.map((u) => [u.id, u.full_name]))))
      .catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    if (!revisions || revisions.length === 0) return;
    (async () => {
      const unique = new Map<string, { entity_type: "warehouse" | "location"; entity_id: string }>();
      for (const r of revisions) {
        unique.set(`${r.entity_type}:${r.entity_id}`, { entity_type: r.entity_type, entity_id: r.entity_id });
      }
      const entries = await Promise.all(
        Array.from(unique.entries()).map(async ([key, { entity_type, entity_id }]) => {
          try {
            const path = entity_type === "warehouse" ? `/warehouses/${entity_id}` : `/locations/${entity_id}`;
            const data = await apiJson<Warehouse | Location>(path);
            const label = entity_type === "warehouse" ? (data as Warehouse).name : (data as Location).description;
            return [key, { generated_code: data.generated_code, label }] as const;
          } catch {
            return [key, { generated_code: entity_id.slice(0, 8), label: "(no longer available)" }] as const;
          }
        }),
      );
      setEntityContext(Object.fromEntries(entries));
    })();
  }, [revisions]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-ink">{isAdmin ? "Review Queue" : "My Revisions"}</h1>
            <p className="mt-0.5 text-sm text-ink-dim">
              {isAdmin
                ? "Revision requests submitted by PICs for their Hospital Unit's warehouses and locations. Nothing changes until you approve, reject, or edit and approve."
                : "Changes you've proposed for your Hospital Unit's warehouses and locations. Nothing is applied until an admin reviews it."}
            </p>
          </div>
          <div className="w-44">
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </Select>
          </div>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}
        {!error && revisions === null && <p className="text-sm text-ink-dim">Loading…</p>}
        {revisions !== null && revisions.length === 0 && (
          <p className="text-sm text-ink-dim">
            No {statusFilter || ""} revisions {isAdmin ? "in the queue" : "submitted"} yet.
          </p>
        )}

        <div className="space-y-3">
          {revisions?.map((r) => (
            <RevisionCard
              key={r.id}
              revision={r}
              isAdmin={isAdmin}
              entityContext={entityContext[`${r.entity_type}:${r.entity_id}`]}
              submittedByName={userMap[r.submitted_by]}
              reviewedByName={r.reviewed_by ? userMap[r.reviewed_by] : null}
              onChanged={() => setReloadToken((t) => t + 1)}
            />
          ))}
        </div>
      </div>
    </AppShell>
  );
}
