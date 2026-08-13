"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    // /dashboard is admin-only on the backend -- a PIC has no landing use
    // for it, so send them straight to their own scoped Warehouses list.
    router.replace(user.role === "admin" ? "/dashboard" : "/warehouses");
  }, [user, isLoading, router]);

  return <div className="flex h-screen items-center justify-center text-sm text-ink-dim">Loading…</div>;
}
