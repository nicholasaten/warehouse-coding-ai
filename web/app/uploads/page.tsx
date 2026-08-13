"use client";

import { AppShell } from "@/components/layout/app-shell";
import { UploadPanel } from "@/components/uploads/upload-panel";

export default function UploadsPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Uploads</h1>
          <p className="mt-0.5 text-sm text-ink-dim">
            Bulk-create warehouses and locations from Excel. One bad row never blocks the rest of the file.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <UploadPanel
            title="Warehouse Master"
            description="Columns: Site Code, Warehouse Type Code, Warehouse Code, Warehouse Name, Description (optional), Capacity (optional). Re-uploading the same Site + Type + Code + Name updates the existing warehouse."
            endpoint="/uploads/warehouse-master"
            onUploaded={() => {}}
          />
          <UploadPanel
            title="Location Master"
            description="Columns: Warehouse Code, Category Rack, Description. Warehouse Code must already exist. A near-duplicate description is held for review instead of created."
            endpoint="/uploads/location-master"
            onUploaded={() => {}}
          />
        </div>
      </div>
    </AppShell>
  );
}
