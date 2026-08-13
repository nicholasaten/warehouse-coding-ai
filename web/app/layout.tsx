import type { Metadata } from "next";

import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Warehouse Layout & Coding Management System",
  description: "Generates Warehouse/Location IDs from a fixed coding formula and explains optimization opportunities",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href={API_URL} />
        <link rel="dns-prefetch" href={API_URL} />
      </head>
      <body className="min-h-screen bg-paper font-sans text-ink antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
