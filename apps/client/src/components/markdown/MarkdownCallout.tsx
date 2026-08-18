"use client";

import React, { memo } from "react";
import {
  InfoIcon,
  LightbulbIcon,
  AlertTriangleIcon,
  AlertOctagonIcon,
  SparklesIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { CalloutProps } from "./types";

const CALLOUT_CONFIG: Record<
  CalloutProps["type"],
  {
    icon: React.ComponentType<{ className?: string }>;
    defaultTitle: string;
    border: string;
    bg: string;
    text: string;
    iconColor: string;
  }
> = {
  note: {
    icon: InfoIcon,
    defaultTitle: "Note",
    border: "border-blue-500/40 border-l-4",
    bg: "bg-blue-500/10 dark:bg-blue-500/15",
    text: "text-blue-900 dark:text-blue-200",
    iconColor: "text-blue-500",
  },
  tip: {
    icon: LightbulbIcon,
    defaultTitle: "Tip",
    border: "border-emerald-500/40 border-l-4",
    bg: "bg-emerald-500/10 dark:bg-emerald-500/15",
    text: "text-emerald-900 dark:text-emerald-200",
    iconColor: "text-emerald-500",
  },
  important: {
    icon: SparklesIcon,
    defaultTitle: "Important",
    border: "border-purple-500/40 border-l-4",
    bg: "bg-purple-500/10 dark:bg-purple-500/15",
    text: "text-purple-900 dark:text-purple-200",
    iconColor: "text-purple-500",
  },
  warning: {
    icon: AlertTriangleIcon,
    defaultTitle: "Warning",
    border: "border-amber-500/40 border-l-4",
    bg: "bg-amber-500/10 dark:bg-amber-500/15",
    text: "text-amber-900 dark:text-amber-200",
    iconColor: "text-amber-500",
  },
  caution: {
    icon: AlertOctagonIcon,
    defaultTitle: "Caution",
    border: "border-rose-500/40 border-l-4",
    bg: "bg-rose-500/10 dark:bg-rose-500/15",
    text: "text-rose-900 dark:text-rose-200",
    iconColor: "text-rose-500",
  },
};

export const MarkdownCallout = memo(
  ({ type, title, children, className }: CalloutProps) => {
    const config = CALLOUT_CONFIG[type] || CALLOUT_CONFIG.note;
    const Icon = config.icon;
    const displayTitle = title || config.defaultTitle;

    return (
      <div
        className={cn(
          "my-3.5 rounded-xl p-3.5 text-xs sm:text-sm shadow-xs transition-all",
          config.border,
          config.bg,
          className
        )}
      >
        <div className="flex items-center gap-2 font-semibold mb-1.5 select-none">
          <Icon className={cn("size-4 shrink-0", config.iconColor)} />
          <span className={cn("text-xs font-bold uppercase tracking-wider", config.iconColor)}>
            {displayTitle}
          </span>
        </div>
        <div className={cn("leading-relaxed pl-6 space-y-1.5 text-foreground/90")}>
          {children}
        </div>
      </div>
    );
  }
);

MarkdownCallout.displayName = "MarkdownCallout";
