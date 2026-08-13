"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiJson, ApiError } from "@/lib/api-client";
import type { Site } from "@/lib/types";

export function SiteForm({ onCreated }: { onCreated: (site: Site) => void }) {
  const [code, setCode] = useState("");
  const [shortCode, setShortCode] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setError(null);
    setIsSubmitting(true);
    try {
      const site = await apiJson<Site>("/config/sites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.toUpperCase(), short_code: shortCode.toUpperCase(), name }),
      });
      onCreated(site);
      setCode("");
      setShortCode("");
      setName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create hospital unit.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Site Code</label>
          <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="e.g. SHLK" />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Short Code</label>
          <Input
            value={shortCode}
            onChange={(e) => setShortCode(e.target.value)}
            placeholder="e.g. LK"
            maxLength={4}
          />
          <p className="mt-1 text-xs text-ink-dim">Used in Location codes -- verify it before real data relies on it.</p>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Hospital Name</label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Siloam Hospitals Lippo Karawaci" />
        </div>
      </div>

      {error && <p className="text-sm text-status-critical">{error}</p>}

      <Button onClick={handleSubmit} disabled={isSubmitting || !code || !shortCode || !name}>
        {isSubmitting ? "Creating…" : "Create Hospital Unit"}
      </Button>
    </div>
  );
}
