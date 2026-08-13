"use client";

import { LogOut, Menu } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { user, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="flex h-14 flex-none items-center justify-between border-b border-line bg-paper px-4 sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-md p-2 text-ink-dim hover:bg-accent-wash hover:text-ink lg:hidden"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="flex-1" />
      <span className="hidden text-sm text-ink-dim sm:inline">
        {user?.full_name}
        {user && <span className="ml-1.5 font-mono text-[0.65rem] uppercase tracking-wide text-accent">{user.role}</span>}
      </span>
      <Button variant="ghost" onClick={handleLogout}>
        <LogOut className="h-4 w-4" />
        <span className="hidden sm:inline">Log out</span>
      </Button>
    </header>
  );
}
