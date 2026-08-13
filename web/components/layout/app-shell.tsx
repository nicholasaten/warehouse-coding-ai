"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

/** Client-side route guard -- access tokens live in memory only, so there's
 * nothing an edge middleware could inspect; the guard runs here, after
 * AuthProvider's silent-refresh attempt has had a chance to resolve. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [isNavOpen, setIsNavOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return <div className="flex h-screen items-center justify-center text-sm text-ink-dim">Loading…</div>;
  }

  if (!user) return null;

  return (
    <div className="min-h-screen">
      <Sidebar isOpen={isNavOpen} onClose={() => setIsNavOpen(false)} />
      <div className="flex min-h-screen flex-col lg:pl-56">
        <Topbar onMenuClick={() => setIsNavOpen(true)} />
        <main className="flex-1 overflow-y-auto overflow-x-hidden bg-paper p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
