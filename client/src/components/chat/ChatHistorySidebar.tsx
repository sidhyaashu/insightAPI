"use client";

import React, { useState } from "react";
import { cn } from "@/lib/utils";
import {
  MessageSquareIcon,
  PlusIcon,
  Trash2Icon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface ChatSession {
  id: string;
  title: string;
  createdAt: number;
  messages: Array<{ id: string; role: string; content: string }>;
}

interface ChatHistorySidebarProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}: ChatHistorySidebarProps) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <aside
      className={cn(
        "relative flex flex-col h-full shrink-0 z-10",
        "border-r border-border/50 bg-sidebar/50 backdrop-blur-sm",
        "transition-all duration-200 ease-in-out overflow-hidden",
        collapsed ? "w-[52px]" : "w-[220px]"
      )}
    >
      {/* ── Top action row ─────────────────────────────────────────────── */}
      <div
        className={cn(
          "flex items-center gap-1.5 px-2 py-3 border-b border-border/40 shrink-0",
          collapsed ? "justify-center" : "justify-between"
        )}
      >
        <Tooltip content={collapsed ? "New conversation" : undefined} side="right">
          <Button
            variant="ghost"
            size="icon"
            onClick={onNewChat}
            className="size-8 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer shrink-0"
            title="New conversation"
          >
            <PlusIcon className="size-4" />
          </Button>
        </Tooltip>

        {!collapsed && (
          <span className="text-[11px] font-semibold text-muted-foreground tracking-wide uppercase truncate">
            History
          </span>
        )}
      </div>

      {/* ── Session list ───────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-2 px-1.5 space-y-0.5 no-scrollbar">
        {sessions.length === 0 && !collapsed && (
          <p className="text-[11px] text-muted-foreground text-center py-6 px-2 leading-relaxed">
            No conversations yet. Start one below ↓
          </p>
        )}

        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;
          const msgCount = session.messages.length;
          const tooltipText = collapsed
            ? `${session.title} · ${msgCount} msg${msgCount !== 1 ? "s" : ""} · ${relativeTime(session.createdAt)}`
            : undefined;

          return (
            <Tooltip key={session.id} content={tooltipText} side="right">
              <button
                type="button"
                onClick={() => onSelectSession(session.id)}
                className={cn(
                  "group w-full flex items-center gap-2.5 rounded-xl text-left transition-all cursor-pointer",
                  collapsed ? "justify-center p-2" : "px-2.5 py-2",
                  isActive
                    ? "bg-primary/10 text-primary border border-primary/20 shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-transparent"
                )}
              >
                <MessageSquareIcon
                  className={cn(
                    "shrink-0 transition-colors",
                    collapsed ? "size-4" : "size-3.5",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground group-hover:text-foreground"
                  )}
                />

                {!collapsed && (
                  <div className="flex-1 min-w-0">
                    <p className="text-[12px] font-medium truncate leading-tight">
                      {session.title}
                    </p>
                    <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                      {msgCount} msg{msgCount !== 1 ? "s" : ""} &middot;{" "}
                      {relativeTime(session.createdAt)}
                    </p>
                  </div>
                )}

                {!collapsed && (
                  <button
                    type="button"
                    onClick={(e) => onDeleteSession(session.id, e)}
                    className={cn(
                      "opacity-0 group-hover:opacity-100 p-1 rounded-md transition-all cursor-pointer shrink-0",
                      "hover:bg-destructive/15 hover:text-destructive text-muted-foreground"
                    )}
                    title="Delete conversation"
                  >
                    <Trash2Icon className="size-3" />
                  </button>
                )}
              </button>
            </Tooltip>
          );
        })}
      </div>

      {/* ── Bottom: collapse toggle ─────────────────────────────────────── */}
      <div className="border-t border-border/40 p-2 shrink-0 flex justify-center">
        <Tooltip
          content={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          side="right"
        >
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed((c) => !c)}
            className="size-8 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted/60 cursor-pointer"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <PanelLeftOpenIcon className="size-4" />
            ) : (
              <PanelLeftCloseIcon className="size-4" />
            )}
          </Button>
        </Tooltip>
      </div>
    </aside>
  );
}
