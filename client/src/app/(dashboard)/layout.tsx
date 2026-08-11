"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/store";
import { AppSidebar } from "@/components/app-sidebar";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { GhostIcon } from "lucide-react";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAppSelector((state) => state.auth);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground font-mono">Loading session...</p>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "15rem",
        } as React.CSSProperties
      }
    >
      <AppSidebar />
      <SidebarInset className="bg-background flex flex-col min-h-screen overflow-hidden">
        {/* Claude Floating Borderless Top Bar */}
        <header className="flex h-11 shrink-0 items-center justify-between px-3 py-2 z-10 select-none">
          <div className="flex items-center gap-2">
            <SidebarTrigger className="h-8 w-8 text-muted-foreground hover:text-foreground hover:bg-muted/60 transition cursor-pointer rounded-lg" />
          </div>

          {/* Centered Free plan · Upgrade Pill */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-muted/40 border border-border/40 text-xs font-mono">
            <span className="text-muted-foreground">{user?.tier || "Free"} plan</span>
            <span className="text-muted-foreground/40">•</span>
            <Link href="/billing" className="text-foreground hover:underline font-medium">
              Upgrade
            </Link>
          </div>

          <div className="flex items-center gap-2 text-muted-foreground">
            <GhostIcon className="size-4 hover:text-foreground cursor-pointer transition-colors" />
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex flex-1 flex-col overflow-y-auto">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
