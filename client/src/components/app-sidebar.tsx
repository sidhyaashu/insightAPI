"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  IconDashboard,
  IconListDetails,
  IconMessages,
  IconCreditCard,
  IconSettings,
  IconFileText,
  IconInnerShadowTop,
  IconLogout,
  IconArrowLeft,
  IconChevronDown,
} from "@tabler/icons-react";

import { useAppSelector, useAppDispatch } from "@/store";
import { authApi } from "@/features/auth/api/auth.api";
import { clearCredentials } from "@/features/auth/store/authSlice";
import { Badge } from "@/components/ui/badge";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarGroup,
} from "@/components/ui/sidebar";
import env from "@/lib/env";

const docsNav = [
  {
    title: "Getting Started",
    url: "#python-sdk",
    items: [
      { title: "Python SDK Setup", url: "#python-sdk" },
      { title: "CLI Engine Setup", url: "#cli-engine" },
      { title: "Architecture Overview", url: "#gateway-endpoints" },
    ],
  },
  {
    title: "Autonomous Engine",
    url: "#python-sdk",
    items: [
      { title: "Accessibility Tree Snapping", url: "#python-sdk" },
      { title: "Two-Tier Safety Guardrails", url: "#cli-engine" },
      { title: "DOM State Hashing & SPAs", url: "#gateway-endpoints" },
    ],
  },
  {
    title: "API Intelligence & Observers",
    url: "#gateway-endpoints",
    items: [
      { title: "Network Traffic Observer", url: "#gateway-endpoints" },
      { title: "Path Parameter Normalization", url: "#gateway-endpoints" },
      { title: "GraphQL Query Parsing", url: "#gateway-endpoints" },
    ],
  },
  {
    title: "API Reference & Exports",
    url: "#gateway-endpoints",
    items: [
      { title: "OpenAPI 3.1 Specification", url: "#gateway-endpoints" },
      { title: "Postman v2.1 Collections", url: "#gateway-endpoints" },
      { title: "Gateway REST Endpoints", url: "#gateway-endpoints" },
    ],
  },
];

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);

  const isDocs = pathname.startsWith("/docs");

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    dispatch(clearCredentials());
    router.replace("/login");
  };

  const navMain = [
    { title: "Dashboard", href: "/dashboard", icon: IconDashboard },
    { title: "Crawl History", href: "/crawls", icon: IconListDetails },
    { title: "AI Chatbot", href: "/chat", icon: IconMessages },
    { title: "Billing & Tier", href: "/billing", icon: IconCreditCard },
    { title: "Settings", href: "/settings", icon: IconSettings },
    { title: "Docs & SDK", href: "/docs", icon: IconFileText },
  ];

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
                <IconInnerShadowTop className="size-5" />
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground">{env.APP_NAME}</span>
                  {user?.tier === "ADMIN" ? (
                    <Badge variant="outline" className="text-[9px] px-1.5 py-0 font-mono border-primary/40 text-primary">
                      ADMIN
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[9px] px-1 py-0 font-mono text-muted-foreground">
                      {user?.tier || "FREE"}
                    </Badge>
                  )}
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {isDocs ? "Documentation Portal" : "Agentic API Intelligence"}
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="px-2 py-4">
        {isDocs ? (
          /* Docs-Specific Sidebar Menu with Dropdown Groups */
          <SidebarGroup>
            <div className="mb-4 px-2">
              <Link
                href="/dashboard"
                className="flex items-center gap-2 text-xs font-semibold text-primary hover:underline"
              >
                <IconArrowLeft className="size-3.5" />
                <span>Back to Dashboard</span>
              </Link>
            </div>

            <SidebarMenu className="gap-2">
              {docsNav.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton render={<a href={item.url} />} className="font-semibold text-foreground flex items-center justify-between">
                    <span>{item.title}</span>
                    <IconChevronDown className="size-3 text-muted-foreground" />
                  </SidebarMenuButton>
                  {item.items?.length ? (
                    <SidebarMenuSub className="ml-0 border-l border-border px-1.5 mt-1 space-y-1">
                      {item.items.map((subItem) => (
                        <SidebarMenuSubItem key={subItem.title}>
                          <SidebarMenuSubButton render={<a href={subItem.url} />} className="text-xs text-muted-foreground hover:text-foreground">
                            {subItem.title}
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  ) : null}
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        ) : (
          /* Main Dashboard Sidebar Menu */
          <SidebarMenu className="gap-1">
            {navMain.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={isActive}
                    className={`font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground hover:bg-accent"
                    }`}
                  >
                    <Icon className="size-4" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-border p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-col truncate">
            <span className="text-xs font-semibold text-foreground truncate">{user?.name || user?.email || "Developer"}</span>
            <span className="text-[10px] text-muted-foreground truncate">{user?.email}</span>
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition"
          >
            <IconLogout className="size-4" />
          </button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
