"use client";

import React, { memo } from "react";
import Link from "next/link";
import { ExternalLinkIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { isSafeUrl } from "./markdown-utils";

export const MarkdownLink = memo(
  ({
    href,
    children,
    className,
    ...props
  }: React.ComponentPropsWithoutRef<"a">) => {
    if (!href || !isSafeUrl(href)) {
      // Disallow unsafe protocols by returning non-clickable text
      return (
        <span className={cn("text-muted-foreground underline decoration-dotted", className)}>
          {children}
        </span>
      );
    }

    const isExternal = href.startsWith("http://") || href.startsWith("https://");

    if (isExternal) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "text-primary hover:text-primary/80 underline underline-offset-3 decoration-primary/40 hover:decoration-primary font-medium transition-colors inline-flex items-baseline gap-0.5 group/link cursor-pointer",
            className
          )}
          {...props}
        >
          <span>{children}</span>
          <ExternalLinkIcon className="size-3 inline-block shrink-0 opacity-70 group-hover/link:opacity-100 transition-opacity ml-0.5 align-text-bottom" />
        </a>
      );
    }

    return (
      <Link
        href={href}
        className={cn(
          "text-primary hover:text-primary/80 underline underline-offset-3 decoration-primary/40 hover:decoration-primary font-medium transition-colors cursor-pointer",
          className
        )}
        {...props}
      >
        {children}
      </Link>
    );
  }
);

MarkdownLink.displayName = "MarkdownLink";
