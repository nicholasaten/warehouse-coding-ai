"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Site, UserAccount } from "@/lib/types";

export function UserForm({ onCreated }: { onCreated: (user: UserAccount) => void }) {
  const [sites, setSites] = useState<Site[]>([]);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "pic">("pic");
  const [siteId, setSiteId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      const data = await apiJson<Site[]>("/config/sites");
      setSites(data);
      if (data.length > 0) setSiteId(data[0].id);
    })();
  }, []);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      const user = await apiJson<UserAccount>("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          role,
          site_id: role === "pic" ? siteId : undefined,
        }),
      });
      onCreated(user);
      setFullName("");
      setEmail("");
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = fullName && email && password.length >= 8 && (role === "admin" || siteId);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Full Name</label>
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Budi Santoso" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Email</label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@siloamhospitals.com" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Password</label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Role</label>
          <Select value={role} onChange={(e) => setRole(e.target.value as "admin" | "pic")}>
            <option value="pic">PIC (scoped to one Hospital Unit)</option>
            <option value="admin">Admin (unscoped)</option>
          </Select>
        </div>
        {role === "pic" && (
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-ink-dim">Hospital Unit</label>
            <Select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} — {s.name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-status-critical">{error}</p>}

      <Button onClick={handleSubmit} disabled={isSubmitting || !canSubmit}>
        {isSubmitting ? "Creating…" : "Create User"}
      </Button>
    </div>
  );
}
