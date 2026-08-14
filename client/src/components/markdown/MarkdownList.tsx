"use client";

import React, { memo } from "react";
import { CheckIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export const MarkdownUl = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"ul">) => {
    return (
      <ul
        className={cn(
          "list-disc pl-5 my-2.5 space-y-1 text-foreground leading-relaxed",
          className
        )}
        {...props}
      >
        {children}
      </ul>
    );
  }
);
MarkdownUl.displayName = "MarkdownUl";

export const MarkdownOl = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"ol">) => {
    return (
      <ol
        className={cn(
          "list-decimal pl-5 my-2.5 space-y-1 text-foreground leading-relaxed",
          className
        )}
        {...props}
      >
        {children}
      </ol>
    );
  }
);
MarkdownOl.displayName = "MarkdownOl";

export const MarkdownLi = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"li">) => {
    // Check if children contain task list checkbox from remark-gfm
    const isTaskList =
      className?.includes("task-list-item") ||
      (Array.isArray(children) &&
        children[0] &&
        typeof children[0] === "object" &&
        "type" in children[0] &&
        children[0].type === "input");

    return (
      <li
        className={cn(
          "leading-relaxed",
          isTaskList && "list-none -ml-4 flex items-start gap-2",
          className
        )}
        {...props}
      >
        {children}
      </li>
    );
  }
);
MarkdownLi.displayName = "MarkdownLi";

export const MarkdownCheckbox = memo(
  ({ checked, className }: { checked?: boolean; className?: string }) => {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center size-4 rounded-xs border mt-0.5 shrink-0 transition-colors select-none",
          checked
            ? "bg-primary text-primary-foreground border-primary"
            : "border-border/80 bg-muted/40",
          className
        )}
        aria-checked={checked}
        role="checkbox"
      >
        {checked && <CheckIcon className="size-3 stroke-[3]" />}
      </span>
    );
  }
);
MarkdownCheckbox.displayName = "MarkdownCheckbox";
