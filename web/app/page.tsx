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
    // /dashboard is role-aware -- admin gets the system-wide summary, PIC
    // gets their own Hospital Unit's pending-review dashboard.
    router.replace("/dashboard");
  }, [user, isLoading, router]);

  return <div className="flex h-screen items-center justify-center text-sm text-ink-dim">Loading…</div>;
}
