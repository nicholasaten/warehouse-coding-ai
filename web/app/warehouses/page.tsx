"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { WarehouseForm } from "@/components/warehouses/warehouse-form";
import { WarehouseTable } from "@/components/warehouses/warehouse-table";
import { apiJson, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";
import type { Site, Warehouse } from "@/lib/types";

export default function WarehousesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [sites, setSites] = useState<Site[]>([]);
  const [siteFilter, setSiteFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [revisionFilter, setRevisionFilter] = useState("");
  const [warehouses, setWarehouses] = useState<Warehouse[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (isAdmin) apiJson<Site[]>("/config/sites").then(setSites).catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    (async () => {
      try {
        const params = new URLSearchParams();
        if (siteFilter) params.set("site_id", siteFilter);
        if (statusFilter) params.set("is_active", statusFilter);
        if (revisionFilter) params.set("has_pending_revision", revisionFilter);
        const query = params.toString();
        const data = await apiJson<Warehouse[]>(`/warehouses${query ? `?${query}` : ""}`);
        setWarehouses(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load warehouses.");
      }
    })();
  }, [siteFilter, statusFilter, revisionFilter, reloadToken]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink">Warehouses</h1>
            <p className="mt-0.5 text-sm text-ink-dim">
              {isAdmin
                ? "Codes are generated automatically from the site, warehouse type, and warehouse code you pick."
                : "Your Hospital Unit's warehouses. Request a revision if something needs correcting."}
            </p>
          </div>
          {isAdmin && (
            <Button onClick={() => setShowForm((v) => !v)}>
              <Plus className="h-4 w-4" />
              New Warehouse
            </Button>
          )}
        </div>

        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>Create Warehouse</CardTitle>
            </CardHeader>
            <CardContent>
              <WarehouseForm
                onCreated={() => {
                  setReloadToken((t) => t + 1);
                  setShowForm(false);
                }}
              />
            </CardContent>
          </Card>
        )}

        <div className="flex flex-wrap gap-3">
          {isAdmin && (
            <div className="w-48">
              <label className="mb-1 block text-xs font-medium text-ink-dim">Hospital Code</label>
              <Select value={siteFilter} onChange={(e) => setSiteFilter(e.target.value)}>
                <option value="">All hospitals</option>
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </Select>
            </div>
          )}
          <div className="w-40">
            <label className="mb-1 block text-xs font-medium text-ink-dim">Status</label>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </Select>
          </div>
          <div className="w-48">
            <label className="mb-1 block text-xs font-medium text-ink-dim">Revision Status</label>
            <Select value={revisionFilter} onChange={(e) => setRevisionFilter(e.target.value)}>
              <option value="">All</option>
              <option value="true">Pending revision</option>
              <option value="false">No pending revision</option>
            </Select>
          </div>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}
        {!error && warehouses === null && <p className="text-sm text-ink-dim">Loading…</p>}
        {warehouses !== null && (
          <WarehouseTable
            warehouses={warehouses}
            isAdmin={isAdmin}
            sites={sites}
            onChanged={() => setReloadToken((t) => t + 1)}
          />
        )}
      </div>
    </AppShell>
  );
}
