"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppSelector } from "@/store";
import { AppSidebar } from "@/components/app-sidebar";
import { UserAvatarMenu } from "@/components/UserAvatarMenu";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);

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
        {/* Main Content Area */}
        <main className="flex flex-1 flex-col min-h-0 w-full overflow-hidden bg-background">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
