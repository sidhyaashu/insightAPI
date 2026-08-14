"use client";

import React, { useMemo, memo } from "react";
import katex from "katex";
import { cn } from "@/lib/utils";
import type { MathBlockProps } from "./types";

export const MarkdownMath = memo(
  ({ math, inline = false, className }: MathBlockProps) => {
    const renderedHtml = useMemo(() => {
      try {
        return katex.renderToString(math.trim(), {
          displayMode: !inline,
          throwOnError: false,
          output: "htmlAndMathml",
        });
      } catch (err) {
        console.warn("KaTeX render error:", err);
        return null;
      }
    }, [math, inline]);

    if (!renderedHtml) {
      return (
        <code
          className={cn(
            "font-mono text-xs bg-muted/60 text-muted-foreground px-1.5 py-0.5 rounded",
            className
          )}
        >
          {inline ? `$${math}$` : `$$${math}$$`}
        </code>
      );
    }

    if (inline) {
      return (
        <span
          className={cn("inline-block my-0.5 px-0.5", className)}
          dangerouslySetInnerHTML={{ __html: renderedHtml }}
        />
      );
    }

    return (
      <div className="my-3 overflow-x-auto p-3 rounded-xl border border-border/60 bg-muted/20 text-center">
        <div
          className={cn("inline-block text-foreground", className)}
          dangerouslySetInnerHTML={{ __html: renderedHtml }}
        />
      </div>
    );
  }
);

MarkdownMath.displayName = "MarkdownMath";
