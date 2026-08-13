"use client";

import { useEffect, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { apiFetch, apiJson, ApiError } from "@/lib/api-client";
import type { RawImportBatch, Site } from "@/lib/types";

export function RawImportUpload({ onUploaded }: { onUploaded: (batch: RawImportBatch) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [siteId, setSiteId] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const data = await apiJson<Site[]>("/config/sites");
      setSites(data);
      if (data.length > 0) setSiteId(data[0].id);
    })();
  }, []);

  async function handleUpload() {
    const file = inputRef.current?.files?.[0];
    if (!file || !siteId) return;

    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("site_id", siteId);
      const res = await apiFetch("/raw-import/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, body?.detail ?? "Upload failed");
      }
      const batch: RawImportBatch = await res.json();
      onUploaded(batch);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
      setFileName(null);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-dim">
        Upload a legacy raw export (Organization/CodeStore/Store/CodeStoreRack/StoreRack/ActiveStoreRack columns) --
        the AI will suggest a Warehouse Type/Code for each distinct store, and later a Category Rack for each rack.
        Nothing is created until you review and approve each suggestion.
      </p>

      <div className="max-w-xs">
        <label className="mb-1 block text-xs font-medium text-ink-dim">Hospital Unit this file belongs to</label>
        <Select value={siteId} onChange={(e) => setSiteId(e.target.value)}>
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.code} — {s.name}
            </option>
          ))}
        </Select>
      </div>

      <label
        htmlFor="raw-import-file"
        className="flex cursor-pointer flex-col items-center gap-2 rounded-md border border-dashed border-line-strong px-4 py-6 text-center hover:bg-accent-wash/40"
      >
        <UploadCloud className="h-6 w-6 text-ink-dim" />
        <span className="text-sm text-ink">{fileName ?? "Click to choose an .xlsx file"}</span>
        <input
          id="raw-import-file"
          ref={inputRef}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
        />
      </label>

      <Button disabled={!fileName || !siteId || isUploading} onClick={handleUpload}>
        {isUploading ? "Uploading and getting AI suggestions…" : "Upload"}
      </Button>

      {error && <p className="text-sm text-status-critical">{error}</p>}
    </div>
  );
}
