"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { SiteForm } from "@/components/config/site-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { apiJson } from "@/lib/api-client";
import type { CategoryRackMapping, LocationTypeConfig, Site, WarehouseCodeConfig, WarehouseTypeConfig } from "@/lib/types";

export default function ConfigPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [types, setTypes] = useState<WarehouseTypeConfig[]>([]);
  const [codes, setCodes] = useState<WarehouseCodeConfig[]>([]);
  const [locTypes, setLocTypes] = useState<LocationTypeConfig[]>([]);
  const [mappings, setMappings] = useState<CategoryRackMapping[]>([]);
  const [showSiteForm, setShowSiteForm] = useState(false);

  useEffect(() => {
    apiJson<Site[]>("/config/sites").then(setSites).catch(() => {});
    apiJson<WarehouseTypeConfig[]>("/config/warehouse-types").then(setTypes).catch(() => {});
    apiJson<WarehouseCodeConfig[]>("/config/warehouse-codes").then(setCodes).catch(() => {});
    apiJson<LocationTypeConfig[]>("/config/location-types").then(setLocTypes).catch(() => {});
    apiJson<CategoryRackMapping[]>("/config/category-rack-mappings").then(setMappings).catch(() => {});
  }, []);

  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink">Config</h1>
          <p className="mt-0.5 text-sm text-ink-dim">
            The fixed coding formula (SOP) this whole system generates codes from. Loaded once by{" "}
            <code className="font-mono text-xs">scripts/seed_config.py</code> — never modified by anything in this
            app automatically.
          </p>
        </div>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Sites (Hospital Units)</CardTitle>
            <Button variant="ghost" onClick={() => setShowSiteForm((v) => !v)}>
              <Plus className="h-4 w-4" />
              New Hospital Unit
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            {showSiteForm && (
              <div className="rounded-md border border-line bg-paper/60 p-4">
                <SiteForm
                  onCreated={(site) => {
                    setSites((prev) => [...prev, site]);
                    setShowSiteForm(false);
                  }}
                />
              </div>
            )}
            <Table>
              <THead>
                <TR>
                  <TH>Code</TH>
                  <TH>Short Code</TH>
                  <TH>Name</TH>
                </TR>
              </THead>
              <TBody>
                {sites.map((s) => (
                  <TR key={s.id}>
                    <TD className="font-mono text-xs">{s.code}</TD>
                    <TD className="font-mono text-xs">{s.short_code}</TD>
                    <TD>{s.name}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Warehouse Types</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Code</TH>
                  <TH>Description</TH>
                </TR>
              </THead>
              <TBody>
                {types.map((t) => (
                  <TR key={t.code}>
                    <TD className="font-mono text-xs">{t.code}</TD>
                    <TD>{t.description}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Warehouse Codes ({codes.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Type</TH>
                  <TH>Code</TH>
                  <TH>Description</TH>
                </TR>
              </THead>
              <TBody>
                {codes.map((c) => (
                  <TR key={`${c.warehouse_type_code}-${c.code}`}>
                    <TD className="font-mono text-xs">{c.warehouse_type_code}</TD>
                    <TD className="font-mono text-xs">{c.code}</TD>
                    <TD>{c.description}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Location Types</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Type</TH>
                  <TH>Code</TH>
                  <TH>Description</TH>
                  <TH>Whole Warehouse?</TH>
                </TR>
              </THead>
              <TBody>
                {locTypes.map((l) => (
                  <TR key={`${l.warehouse_type_code}-${l.code}`}>
                    <TD className="font-mono text-xs">{l.warehouse_type_code}</TD>
                    <TD className="font-mono text-xs">{l.code}</TD>
                    <TD>{l.description}</TD>
                    <TD className="text-ink-dim">{l.is_whole_warehouse ? "Yes — omits sequence" : "No"}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Category Rack Mappings</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <THead>
                <TR>
                  <TH>Type</TH>
                  <TH>Raw Category Text</TH>
                </TR>
              </THead>
              <TBody>
                {mappings.map((m) => (
                  <TR key={m.id}>
                    <TD className="font-mono text-xs">{m.warehouse_type_code}</TD>
                    <TD>{m.raw_category_text}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
