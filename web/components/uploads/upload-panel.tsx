"use client";

import { useRef, useState } from "react";
import { CheckCircle2, UploadCloud, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { UploadBatch, UploadError } from "@/lib/types";

export function UploadPanel({
  title,
  description,
  endpoint,
  onUploaded,
}: {
  title: string;
  description: string;
  endpoint: string;
  onUploaded: (batch: UploadBatch) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<UploadBatch | null>(null);
  const [errors, setErrors] = useState<UploadError[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setResult(null);
    setErrors(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiFetch(endpoint, { method: "POST", body: formData });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new ApiError(res.status, body?.detail ?? "Upload failed");
      }
      const batch: UploadBatch = await res.json();
      setResult(batch);
      onUploaded(batch);
      if (batch.error_count > 0) {
        const errRes = await apiFetch(`/uploads/${batch.id}/errors`);
        if (errRes.ok) setErrors(await errRes.json());
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
      setFileName(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-ink-dim">{description}</p>

        <label
          htmlFor={`file-${endpoint}`}
          className="flex cursor-pointer flex-col items-center gap-2 rounded-md border border-dashed border-line-strong px-4 py-6 text-center hover:bg-accent-wash/40"
        >
          <UploadCloud className="h-6 w-6 text-ink-dim" />
          <span className="text-sm text-ink">{fileName ?? "Click to choose an .xlsx file"}</span>
          <input
            id={`file-${endpoint}`}
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
        </label>

        <Button className="w-full" disabled={!fileName || isUploading} onClick={handleUpload}>
          {isUploading ? "Uploading…" : "Upload"}
        </Button>

        {error && <p className="text-sm text-status-critical">{error}</p>}

        {result && (
          <div className="rounded-md border border-line bg-accent-wash/30 p-3 text-sm">
            <div className="flex items-center gap-2 text-ink">
              {result.error_count === 0 ? (
                <CheckCircle2 className="h-4 w-4 text-status-good" />
              ) : (
                <XCircle className="h-4 w-4 text-status-critical" />
              )}
              <span>
                {result.success_count} succeeded, {result.error_count} failed
                {result.pending_count > 0 && `, ${result.pending_count} pending review`} of {result.row_count} rows
              </span>
            </div>
            {result.pending_count > 0 && (
              <p className="mt-1.5 text-xs text-status-warning">
                Some rows looked like possible duplicates — review them on the Merge Suggestions page.
              </p>
            )}
            {errors && errors.length > 0 && (
              <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto border-t border-line pt-2 text-xs text-ink-dim">
                {errors.map((e, i) => (
                  <li key={i}>
                    Row {e.row_number} ({e.column_name}): {e.error_message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
