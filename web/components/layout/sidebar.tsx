"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Boxes, ClipboardCheck, GitMerge, LayoutDashboard, Settings, Sparkles, UploadCloud, Users, Warehouse, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";

const adminOnlyItems = new Set(["/uploads", "/raw-import", "/merge-suggestions", "/config", "/users"]);

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/warehouses", label: "Warehouses", icon: Warehouse },
  { href: "/locations", label: "Locations", icon: Boxes },
  { href: "/revisions", label: "Revisions", icon: ClipboardCheck },
  { href: "/uploads", label: "Uploads", icon: UploadCloud },
  { href: "/raw-import", label: "Raw Import", icon: Sparkles },
  { href: "/merge-suggestions", label: "Merge Suggestions", icon: GitMerge },
  { href: "/config", label: "Config", icon: Settings },
  { href: "/users", label: "Users", icon: Users },
];

export function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user } = useAuth();
  const visibleItems = navItems.filter((item) => user?.role === "admin" || !adminOnlyItems.has(item.href));

  return (
    <>
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-black/40 lg:hidden" onClick={onClose} aria-hidden="true" />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 max-w-[80vw] flex-none flex-col border-r border-line bg-card transition-transform duration-200 ease-out",
          "lg:w-56 lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div>
            <p className="font-mono text-[0.62rem] uppercase tracking-[0.18em] text-accent">Warehouse Coding</p>
            <p className="mt-0.5 text-sm font-semibold text-ink">AI Layout System</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-ink-dim hover:bg-accent-wash hover:text-ink lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 px-3">
          {visibleItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "mb-0.5 flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active ? "bg-accent-wash font-medium text-accent" : "text-ink-dim hover:bg-accent-wash/60 hover:text-ink",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
