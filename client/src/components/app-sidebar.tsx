"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  IconPlus,
  IconGitCompare,
  IconShieldLock,
  IconBrain,
  IconWorld,
  IconKey,
  IconFileText,
  IconHeadset,
  IconSettings,
  IconLogout,
  IconChevronLeft,
  IconChevronRight,
  IconSearch,
  IconTrash,
  IconMessage,
} from "@tabler/icons-react";
import { useAppDispatch, useAppSelector } from "@/store";
import { authApi } from "@/features/auth/api/auth.api";
import { clearCredentials } from "@/features/auth/store/authSlice";
import {
  resetNewChat,
  deleteSessionThunk,
  loadSessionsThunk,
  loadSessionHistoryThunk,
} from "@/features/chatbot/store/chatSlice";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import env from "@/lib/env";

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentUrlSession = searchParams.get("session");
  const dispatch = useAppDispatch();
  const { toggleSidebar } = useSidebar();

  // Sessions from Redux (DB source of truth)
  const { sessions, activeSessionId } = useAppSelector((state) => state.chat);
  const [searchQuery, setSearchQuery] = React.useState("");

  // Load sessions on mount
  React.useEffect(() => {
    dispatch(loadSessionsThunk());
  }, [dispatch]);

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {}
    dispatch(clearCredentials());
    router.replace("/login");
  };

  const handleNewChat = (e?: React.MouseEvent) => {
    e?.preventDefault();
    dispatch(resetNewChat());
    router.push("/chat");
  };

  const handleSelectSession = (sessionId: string) => {
    if (sessionId === activeSessionId && currentUrlSession === sessionId) return;
    dispatch(loadSessionHistoryThunk(sessionId));
    router.push(`/chat?session=${sessionId}`);
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    e.preventDefault();
    await dispatch(deleteSessionThunk(id));
    if (id === activeSessionId || id === currentUrlSession) {
      dispatch(resetNewChat());
      router.push("/chat");
    }
  };

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const navItems = [
    {
      title: "New Chat",
      href: "/chat",
      icon: IconPlus,
      isNewChat: true,
    },
    { title: "Drift Reports", href: "/reports", icon: IconGitCompare },
    { title: "Security Center", href: "/security", icon: IconShieldLock },
    { title: "Platform Intelligence", href: "/intelligence", icon: IconBrain },
    { title: "Verified Domains", href: "/domains", icon: IconWorld },
    { title: "Auth Profiles", href: "/auth-profiles", icon: IconKey },
    { title: "Audit Trail", href: "/audit-logs", icon: IconFileText },
  ];

  return (
    <Sidebar
      collapsible="icon"
      className="border-r border-border/40 bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out select-none"
      {...props}
    >
      {/* ── Header: Logo + Collapse (Expanded) / Expand Toggle (Collapsed) ── */}
      <SidebarHeader className="p-3 border-b border-border/30 group-data-[collapsible=icon]:p-2">
        {/* Expanded Header: Logo + Title on left, Collapse button on right */}
        <div className="flex items-center justify-between gap-2 w-full group-data-[collapsible=icon]:hidden">
          <Link
            href="/chat"
            onClick={handleNewChat}
            className="flex items-center gap-2.5 min-w-0 transition-transform hover:opacity-90"
          >
            {/* Logo Badge */}
            <div className="flex aspect-square size-8 items-center justify-center rounded-xl bg-white text-black dark:bg-white dark:text-black shadow-md shrink-0 font-extrabold text-sm tracking-tight border border-border/20">
              <span className="bg-gradient-to-tr from-blue-600 to-indigo-600 bg-clip-text text-transparent font-sans font-black text-sm">
                IA
              </span>
            </div>

            {/* Brand Title */}
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-sm text-foreground tracking-tight truncate">
                {env.APP_NAME || "InsightAPI AI"}
              </span>
            </div>
          </Link>

          {/* Collapse Button */}
          <button
            type="button"
            onClick={toggleSidebar}
            className="size-7 rounded-lg border border-border/50 bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors cursor-pointer shrink-0"
            title="Collapse sidebar"
          >
            <IconChevronLeft className="size-4" />
          </button>
        </div>

        {/* Collapsed Header: Avatar is HIDDEN, ONLY the Expand button is shown here */}
        <div className="hidden group-data-[collapsible=icon]:flex justify-center w-full">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={toggleSidebar}
                className="size-8 rounded-xl border border-border/50 bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground flex items-center justify-center transition-colors cursor-pointer"
              >
                <IconChevronRight className="size-4.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="font-medium text-xs">
              Expand sidebar
            </TooltipContent>
          </Tooltip>
        </div>
      </SidebarHeader>

      {/* ── Main Content: Navigation Menu & Chat History ─────────────────── */}
      <SidebarContent className="px-2 py-3 space-y-4 overflow-y-auto overflow-x-hidden no-scrollbar group-data-[collapsible=icon]:px-1 group-data-[collapsible=icon]:space-y-3">
        {/* Top Nav Items (First Item is "New Chat") */}
        <div className="space-y-1 w-full">
          {navItems.map((item) => {
            const isNewChatBtn = !!item.isNewChat;
            const isActive =
              isNewChatBtn
                ? pathname === "/chat" && !currentUrlSession && !activeSessionId
                : pathname === item.href;
            const Icon = item.icon;

            return (
              <div key={item.title} className="w-full flex justify-center">
                {/* Expanded Item */}
                <Link
                  href={item.href}
                  onClick={isNewChatBtn ? handleNewChat : undefined}
                  className={`group-data-[collapsible=icon]:hidden h-9 px-3 rounded-xl font-medium text-xs transition-all flex items-center gap-3 w-full ${
                    isNewChatBtn
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs hover:bg-primary/90"
                      : isActive
                      ? "bg-muted/80 text-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                  }`}
                >
                  <Icon className="size-4 shrink-0" />
                  <span className="truncate">{item.title}</span>
                </Link>

                {/* Collapsed Icon Item with Tooltip */}
                <div className="hidden group-data-[collapsible=icon]:flex justify-center w-full">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Link
                        href={item.href}
                        onClick={isNewChatBtn ? handleNewChat : undefined}
                        className={`size-9 rounded-xl flex items-center justify-center transition-all ${
                          isNewChatBtn
                            ? "bg-primary text-primary-foreground font-semibold shadow-xs hover:bg-primary/90"
                            : isActive
                            ? "bg-muted/80 text-foreground font-semibold shadow-xs"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                        }`}
                      >
                        <Icon className="size-4.5 shrink-0" />
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="font-medium text-xs">
                      {item.title}
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Chat History Section (Expanded View Only — Clean, No Redundant + Button) ── */}
        <div className="group-data-[collapsible=icon]:hidden pt-3 border-t border-border/30 space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70">
              Chat History
            </span>
          </div>

          {/* Search conversations input */}
          <div className="relative px-0.5">
            <IconSearch className="size-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/60 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="w-full pl-8 pr-2.5 py-1.5 text-xs rounded-xl bg-muted/30 border border-border/40 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary/40 transition-colors"
            />
          </div>

          {/* Conversation list */}
          <div className="space-y-0.5 max-h-64 overflow-y-auto pr-0.5 no-scrollbar">
            {filteredSessions.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground/60 font-normal">
                No past conversations
              </div>
            ) : (
              filteredSessions.map((session) => {
                const isSelected =
                  session.id === activeSessionId || session.id === currentUrlSession;

                return (
                  <div
                    key={session.id}
                    onClick={() => handleSelectSession(session.id)}
                    className={`group flex items-center justify-between gap-2 px-2.5 py-2 rounded-xl text-xs transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-muted/90 text-foreground font-medium shadow-xs"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <IconMessage
                        className={`size-3.5 shrink-0 ${
                          isSelected ? "text-primary opacity-100" : "opacity-60 group-hover:opacity-100"
                        }`}
                      />
                      <span className="truncate">{session.title}</span>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(e, session.id)}
                      className="opacity-0 group-hover:opacity-100 size-4 text-muted-foreground hover:text-rose-500 transition-opacity shrink-0"
                      title="Delete conversation"
                    >
                      <IconTrash className="size-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </SidebarContent>

      {/* ── Bottom Section: Support, Settings, Logout ────────────────────── */}
      <SidebarFooter className="p-2 border-t border-border/30 space-y-1 group-data-[collapsible=icon]:p-1 group-data-[collapsible=icon]:space-y-1.5">
        {/* Support */}
        <div className="w-full flex justify-center">
          <a
            href="mailto:support@insightapi.ai"
            className="group-data-[collapsible=icon]:hidden h-9 px-3 rounded-xl font-medium text-xs text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors flex items-center gap-3 w-full"
          >
            <IconHeadset className="size-4 shrink-0" />
            <span>Support</span>
          </a>
          <div className="hidden group-data-[collapsible=icon]:flex justify-center w-full">
            <Tooltip>
              <TooltipTrigger asChild>
                <a
                  href="mailto:support@insightapi.ai"
                  className="size-9 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
                >
                  <IconHeadset className="size-4.5" />
                </a>
              </TooltipTrigger>
              <TooltipContent side="right" className="font-medium text-xs">
                Support
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Settings */}
        <div className="w-full flex justify-center">
          <Link
            href="/settings"
            className={`group-data-[collapsible=icon]:hidden h-9 px-3 rounded-xl font-medium text-xs transition-colors flex items-center gap-3 w-full ${
              pathname === "/settings"
                ? "bg-muted text-foreground font-semibold shadow-xs"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <IconSettings className="size-4 shrink-0" />
            <span>Settings</span>
          </Link>
          <div className="hidden group-data-[collapsible=icon]:flex justify-center w-full">
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  href="/settings"
                  className={`size-9 rounded-xl flex items-center justify-center transition-colors ${
                    pathname === "/settings"
                      ? "bg-muted text-foreground font-bold shadow-xs"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                  }`}
                >
                  <IconSettings className="size-4.5" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right" className="font-medium text-xs">
                Settings
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Logout */}
        <div className="w-full flex justify-center">
          <button
            type="button"
            onClick={handleLogout}
            className="group-data-[collapsible=icon]:hidden w-full h-9 px-3 rounded-xl font-medium text-xs text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 transition-colors flex items-center gap-3 cursor-pointer text-left"
          >
            <IconLogout className="size-4 shrink-0" />
            <span>Logout</span>
          </button>
          <div className="hidden group-data-[collapsible=icon]:flex justify-center w-full">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="size-9 rounded-xl flex items-center justify-center text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer"
                >
                  <IconLogout className="size-4.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" className="font-medium text-xs">
                Logout
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
