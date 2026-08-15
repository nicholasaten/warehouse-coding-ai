"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Warehouse } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Invalid email or password." : "Could not reach the server.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-accent-wash text-accent">
            <Warehouse className="h-5 w-5" />
          </div>
          <p className="font-mono text-[0.68rem] uppercase tracking-[0.2em] text-accent">Warehouse Coding AI</p>
          <h1 className="mt-2 text-2xl font-semibold text-ink">Sign in</h1>
          <p className="mt-1 text-sm text-ink-dim">Admin and Hospital Unit PIC access</p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-card border border-line bg-card p-6 shadow-sm">
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-dim">
                Email
              </label>
              <Input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@siloamhospitals.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1.5 block text-xs font-medium uppercase tracking-wide text-ink-dim">
                Password
              </label>
              <Input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && (
            <p className="mt-4 rounded-md bg-status-critical-wash px-3 py-2 text-sm text-status-critical">{error}</p>
          )}

          <Button type="submit" disabled={isSubmitting} className="mt-6 w-full">
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
