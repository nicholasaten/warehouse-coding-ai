"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { PicDashboard } from "@/components/dashboard/pic-dashboard";
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel";
import { StatTile } from "@/components/ui/stat-tile";
import { apiJson, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { DashboardSummary } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const isPic = user?.role === "pic";

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isPic) return;
    (async () => {
      try {
        const data = await apiJson<DashboardSummary>("/dashboard/summary");
        setSummary(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load the dashboard.");
      }
    })();
  }, [isPic]);

  if (isPic) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-xl font-semibold text-ink">Dashboard</h1>
            <p className="mt-0.5 text-sm text-ink-dim">
              Your Hospital Unit&apos;s warehouses and locations, and anything waiting on your review.
            </p>
          </div>
          <PicDashboard />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Dashboard</h1>
          <p className="mt-0.5 text-sm text-ink-dim">Warehouse and location summary, and AI optimization recommendations.</p>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}

        {!error && !summary && <p className="text-sm text-ink-dim">Loading…</p>}

        {summary && (
          <>
            <section>
              <h2 className="mb-2 font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
                Warehouse Summary
              </h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <StatTile label="Total" value={summary.warehouses.total_warehouses} />
                <StatTile label="Active" value={summary.warehouses.active_warehouses} tone="good" />
                <StatTile label="Empty" value={summary.warehouses.empty_warehouses} />
                <StatTile label="Underutilized" value={summary.warehouses.underutilized_warehouses} tone="warning" />
                <StatTile label="Overloaded" value={summary.warehouses.overloaded_warehouses} tone="critical" />
                <StatTile label="No Capacity Set" value={summary.warehouses.warehouses_without_capacity_set} />
              </div>
            </section>

            <section>
              <h2 className="mb-2 font-mono text-[0.7rem] font-semibold uppercase tracking-wide text-ink-dim">
                Location Summary
              </h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <StatTile label="Total Locations" value={summary.locations.total_locations} />
                <StatTile
                  label="Pending Duplicate Review"
                  value={summary.locations.pending_duplicate_review}
                  tone={summary.locations.pending_duplicate_review > 0 ? "warning" : "default"}
                />
              </div>
            </section>

            <RecommendationsPanel />
          </>
        )}
      </div>
    </AppShell>
  );
}
