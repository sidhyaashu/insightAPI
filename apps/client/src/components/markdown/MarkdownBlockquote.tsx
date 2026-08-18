"use client";

import React, { memo } from "react";
import { cn } from "@/lib/utils";
import { MarkdownCallout } from "./MarkdownCallout";
import type { CalloutProps } from "./types";

function getTextFromReactNode(node: React.ReactNode): string {
  if (!node) return "";
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(getTextFromReactNode).join("");
  if (React.isValidElement(node)) {
    const props = node.props as { children?: React.ReactNode };
    if (props && props.children) {
      return getTextFromReactNode(props.children);
    }
  }
  return "";
}

function extractCalloutInfo(children: React.ReactNode): {
  type: CalloutProps["type"];
  content: React.ReactNode;
} | null {
  if (!children) return null;

  const fullText = getTextFromReactNode(children).trim();

  const alertMatch = fullText.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i);
  if (alertMatch) {
    const type = alertMatch[1].toLowerCase() as CalloutProps["type"];
    return {
      type,
      content: children,
    };
  }

  // Also check for **Note:** or **Tip:** or **Warning:**
  const noteMatch = fullText.match(/^\*\*(Note|Tip|Warning|Caution|Important):\*\*/i);
  if (noteMatch) {
    const type = noteMatch[1].toLowerCase() as CalloutProps["type"];
    return {
      type,
      content: children,
    };
  }

  return null;
}

export const MarkdownBlockquote = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"blockquote">) => {
    const callout = extractCalloutInfo(children);

    if (callout) {
      return (
        <MarkdownCallout type={callout.type} className={className}>
          {children}
        </MarkdownCallout>
      );
    }

    return (
      <blockquote
        className={cn(
          "my-3.5 border-l-4 border-primary/40 bg-muted/20 pl-4 pr-2 py-2 rounded-r-lg text-foreground/90 italic",
          className
        )}
        {...props}
      >
        {children}
      </blockquote>
    );
  }
);

MarkdownBlockquote.displayName = "MarkdownBlockquote";
