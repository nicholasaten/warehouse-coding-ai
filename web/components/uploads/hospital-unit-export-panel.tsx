"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { apiFetch, apiJson, ApiError } from "@/lib/api-client";
import type { Site } from "@/lib/types";

/** Downloads the current Warehouse/Location state for one Hospital Unit
 * as a Warehouse Master + Location Master .xlsx -- the exact same
 * format the two upload panels on this page accept, so the file can be
 * edited and re-uploaded unchanged whenever needed. */
export function HospitalUnitExportPanel() {
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState("");
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiJson<Site[]>("/config/sites")
      .then((data) => {
        setSites(data);
        if (data.length > 0) setSiteId(data[0].id);
      })
      .catch(() => {});
  }, []);

  async function handleDownload() {
    if (!siteId) return;
    setIsDownloading(true);
    setError(null);
    try {
      const res = await apiFetch(`/exports/hospital-unit?site_id=${siteId}`);
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, body?.detail ?? "Could not download this export.");
      }
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match?.[1] ?? "hospital-unit-export.xlsx";

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not download this export.");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Download Hospital Unit Export</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-ink-dim">
          Downloads a Warehouse Master + Location Master .xlsx for one Hospital Unit&apos;s current warehouses and
          locations -- the same format the two upload panels above accept, so it can be edited and re-uploaded
          whenever needed.
        </p>

        <div>
          <label className="mb-1 block text-xs font-medium text-ink-dim">Hospital Unit</label>
          <Select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} — {s.name}
              </option>
            ))}
          </Select>
        </div>

        <Button className="w-full" disabled={!siteId || isDownloading} onClick={handleDownload}>
          <Download className="h-4 w-4" />
          {isDownloading ? "Downloading…" : "Download Export"}
        </Button>

        {error && <p className="text-sm text-status-critical">{error}</p>}
      </CardContent>
    </Card>
  );
}
