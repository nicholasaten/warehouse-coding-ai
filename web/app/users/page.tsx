"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { UserForm } from "@/components/users/user-form";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Site, UserAccount } from "@/lib/types";

export default function UsersPage() {
  const [users, setUsers] = useState<UserAccount[] | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    apiJson<Site[]>("/config/sites").then(setSites).catch(() => {});
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiJson<UserAccount[]>("/users");
        setUsers(data);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Could not load users.");
      }
    })();
  }, [reloadToken]);

  const siteById = Object.fromEntries(sites.map((s) => [s.id, s]));

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink">Users</h1>
            <p className="mt-0.5 text-sm text-ink-dim">
              Admin accounts are unscoped. PIC accounts are scoped to exactly one Hospital Unit and can only submit
              revision requests there, never edit directly.
            </p>
          </div>
          <Button onClick={() => setShowForm((v) => !v)}>
            <Plus className="h-4 w-4" />
            New User
          </Button>
        </div>

        {showForm && (
          <Card>
            <CardHeader>
              <CardTitle>Create User</CardTitle>
            </CardHeader>
            <CardContent>
              <UserForm
                onCreated={() => {
                  setReloadToken((t) => t + 1);
                  setShowForm(false);
                }}
              />
            </CardContent>
          </Card>
        )}

        {error && <p className="text-sm text-status-critical">{error}</p>}
        {!error && users === null && <p className="text-sm text-ink-dim">Loading…</p>}
        {users !== null && users.length === 0 && <p className="text-sm text-ink-dim">No users yet.</p>}
        {users !== null && users.length > 0 && (
          <Table>
            <THead>
              <TR>
                <TH>Name</TH>
                <TH>Email</TH>
                <TH>Role</TH>
                <TH>Hospital Unit</TH>
                <TH>Status</TH>
              </TR>
            </THead>
            <TBody>
              {users.map((u) => (
                <TR key={u.id}>
                  <TD>{u.full_name}</TD>
                  <TD className="text-ink-dim">{u.email}</TD>
                  <TD>
                    <Badge tone={u.role === "admin" ? "good" : "neutral"} label={u.role} />
                  </TD>
                  <TD className="text-ink-dim">{u.site_id ? (siteById[u.site_id]?.code ?? "—") : "—"}</TD>
                  <TD>{u.is_active ? <Badge tone="good" label="Active" /> : <Badge tone="neutral" label="Inactive" />}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </div>
    </AppShell>
  );
}
