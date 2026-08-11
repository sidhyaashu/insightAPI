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
  IconUser,
  IconKey,
  IconHelp,
  IconDownload,
  IconChevronRight,
  IconPlus,
} from "@tabler/icons-react";

import { useAppSelector, useAppDispatch } from "@/store";
import { authApi } from "@/features/auth/api/auth.api";
import { clearCredentials } from "@/features/auth/store/authSlice";
import { Badge } from "@/components/ui/badge";
import { ThemeToggle } from "@/components/ThemeToggle";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import env from "@/lib/env";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((state) => state.auth.user);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    dispatch(clearCredentials());
    router.replace("/login");
  };

  const getInitials = (name?: string | null, email?: string | null) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    }
    if (email) {
      return email.slice(0, 2).toUpperCase();
    }
    return "AS";
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
    <Sidebar collapsible="icon" className="border-r border-border/40 bg-sidebar" {...props}>
      <SidebarHeader className="p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs shrink-0">
                <IconInnerShadowTop className="size-5" />
              </div>
              <div className="flex flex-col gap-0.5 leading-none">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground font-mono tracking-tight">{env.APP_NAME}</span>
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
                  Agentic API Intelligence
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        {/* Quick New Chat Button */}
        <div className="mt-2 group-data-[collapsible=icon]:hidden px-1">
          <Link
            href="/chat"
            className="flex items-center gap-2 w-full px-3 py-2 rounded-xl bg-card border border-border/60 hover:bg-muted/60 text-xs font-medium text-foreground transition-colors shadow-xs"
          >
            <IconPlus className="size-4 text-muted-foreground" />
            <span>New Chat</span>
          </Link>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 py-2">
        <SidebarGroup>
          <SidebarMenu className="gap-1">
            {navMain.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    render={<Link href={item.href} />}
                    isActive={isActive}
                    tooltip={item.title}
                    className={`font-medium transition-colors ${
                      isActive
                        ? "bg-muted text-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                    }`}
                  >
                    <Icon className="size-4" />
                    <span>{item.title}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              );
            })}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      {/* Claude-style Sidebar Footer User Profile */}
      <SidebarFooter className="border-t border-border/40 p-2">
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center justify-between gap-2.5 w-full p-1.5 rounded-xl hover:bg-muted/60 transition cursor-pointer focus:outline-none border-none bg-transparent text-left">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="relative flex size-8 shrink-0 items-center justify-center rounded-full bg-muted border border-border text-foreground font-bold text-xs shadow-xs">
                {getInitials(user?.name, user?.email)}
                <span className="absolute bottom-0 right-0 size-2 rounded-full bg-emerald-500 ring-2 ring-background" />
              </div>
              <div className="flex flex-col min-w-0 group-data-[collapsible=icon]:hidden">
                <span className="text-xs font-semibold text-foreground truncate">
                  {user?.name || "Asutosh Sidhya"}
                </span>
                <span className="text-[10px] text-muted-foreground font-mono truncate">
                  {user?.tier || "Free"} plan
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1 group-data-[collapsible=icon]:hidden text-muted-foreground">
              <IconDownload className="size-4 hover:text-foreground transition-colors" title="Download desktop app" />
            </div>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="start" side="right" className="w-64 p-2 shadow-2xl rounded-2xl bg-card border border-border">
            <DropdownMenuGroup>
              <DropdownMenuLabel className="font-normal p-2">
                <div className="flex flex-col gap-1">
                  <p className="text-xs font-semibold leading-none text-foreground">
                    {user?.name || "Asutosh Sidhya"}
                  </p>
                  <p className="text-[11px] leading-none text-muted-foreground truncate font-mono">
                    {user?.email || "sidhyaasutosh@gmail.com"}
                  </p>
                  <div className="pt-1.5 flex items-center gap-2">
                    <Badge variant="outline" className="text-[9px] px-1.5 py-0.2 font-mono border-border">
                      {user?.tier || "Free"} Plan
                    </Badge>
                    <Link href="/billing" className="text-[10px] text-primary hover:underline font-medium">
                      Upgrade plan
                    </Link>
                  </div>
                </div>
              </DropdownMenuLabel>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuGroup>
              <DropdownMenuItem onClick={() => router.push("/settings")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconUser className="size-4 text-muted-foreground" />
                <span>Profile & Account</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/billing")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconCreditCard className="size-4 text-muted-foreground" />
                <span>Billing & Subscriptions</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/settings")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconKey className="size-4 text-muted-foreground" />
                <span>API Keys & SDK Setup</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push("/docs")} className="cursor-pointer text-xs flex items-center gap-2 py-2">
                <IconFileText className="size-4 text-muted-foreground" />
                <span>Documentation Reference</span>
              </DropdownMenuItem>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <div className="px-2 py-1.5 flex items-center justify-between text-xs text-muted-foreground">
              <span>Appearance</span>
              <ThemeToggle />
            </div>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={handleLogout}
              className="cursor-pointer text-xs flex items-center gap-2 py-2 text-destructive focus:bg-destructive/10"
            >
              <IconLogout className="size-4" />
              <span>Sign Out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
