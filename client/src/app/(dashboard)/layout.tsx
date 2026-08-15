"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/store";
import { usePathname } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { UserAvatarMenu } from "@/components/UserAvatarMenu";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";

const ROUTE_LABELS: Record<string, { category: string; title: string }> = {
  "/chat": { category: "Workspace", title: "AI Assistant" },
  "/reports": { category: "Intelligence", title: "Crawl Reports" },
  "/security": { category: "Intelligence", title: "Security Center" },
  "/intelligence": { category: "Platform", title: "Intelligence & Memory" },
  "/domains": { category: "Compliance", title: "Verified Domains" },
  "/auth-profiles": { category: "Credentials", title: "Auth Profiles" },
  "/audit-logs": { category: "Compliance", title: "Audit Trail" },
  "/billing": { category: "Account", title: "Billing & Plans" },
  "/settings": { category: "Preferences", title: "Workspace Settings" },
  "/tos": { category: "Legal", title: "Terms of Service" },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading, user } = useAppSelector((state) => state.auth);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background font-mono text-sm text-muted-foreground">
        Loading workspace...
      </div>
    );
  }

  if (!isAuthenticated) return null;

  // Derive active route breadcrumb label
  let activeRoute = ROUTE_LABELS[pathname];
  if (!activeRoute) {
    if (pathname.startsWith("/reports/") && pathname.includes("/drift")) {
      activeRoute = { category: "Intelligence", title: "API Drift Diff" };
    } else if (pathname.startsWith("/reports/")) {
      activeRoute = { category: "Intelligence", title: "Report Details" };
    } else if (pathname.startsWith("/crawls/") && pathname.includes("/review")) {
      activeRoute = { category: "Crawl Engine", title: "Schema Review" };
    } else {
      activeRoute = { category: "Workspace", title: "InsightAPI" };
    }
  }

  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "17rem",
          "--sidebar-width-icon": "4rem",
        } as React.CSSProperties
      }
    >
      <AppSidebar />
      <SidebarInset className="bg-background flex flex-col h-screen overflow-hidden relative">
        {/* ── Top Header Navigation Bar ── */}
        <header className="h-12 border-b border-border/40 bg-background/80 backdrop-blur-md px-4 flex items-center justify-between gap-4 shrink-0 z-30 select-none">
          <div className="flex items-center gap-3 min-w-0">
            <SidebarTrigger className="size-8 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer" />
            <div className="h-4 w-px bg-border/60 hidden sm:block" />
            <div className="flex items-center gap-1.5 text-xs truncate font-sans">
              <span className="text-muted-foreground/70 hidden sm:inline font-medium">
                {activeRoute.category}
              </span>
              <span className="text-muted-foreground/40 hidden sm:inline">/</span>
              <span className="text-foreground font-semibold truncate">
                {activeRoute.title}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Account Tier Badge */}
            {user?.tier && (
              <span
                className={`hidden sm:inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider ${
                  user.tier === "ADMIN"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/30 font-extrabold"
                    : user.tier === "PRO"
                    ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/30"
                    : "bg-primary/10 text-primary border border-primary/20"
                }`}
              >
                {user.tier}
              </span>
            )}
            <ThemeToggle />
            <UserAvatarMenu />
          </div>
        </header>

        {/* ── Main Scrollable Content Area ── */}
        <main className="flex flex-1 flex-col min-h-0 w-full overflow-y-auto bg-background">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
