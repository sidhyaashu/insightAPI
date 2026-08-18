"use client";

import React, { memo } from "react";
import { cn } from "@/lib/utils";

export const MarkdownH1 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h1">) => (
    <h1
      className={cn(
        "text-lg sm:text-xl font-bold text-foreground mt-4 mb-2 pb-1.5 border-b border-border/50 tracking-tight",
        className
      )}
      {...props}
    >
      {children}
    </h1>
  )
);
MarkdownH1.displayName = "MarkdownH1";

export const MarkdownH2 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h2">) => (
    <h2
      className={cn(
        "text-base sm:text-lg font-semibold text-foreground mt-3.5 mb-1.5 tracking-tight",
        className
      )}
      {...props}
    >
      {children}
    </h2>
  )
);
MarkdownH2.displayName = "MarkdownH2";

export const MarkdownH3 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h3">) => (
    <h3
      className={cn(
        "text-sm sm:text-base font-semibold text-foreground mt-3 mb-1 tracking-tight",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  )
);
MarkdownH3.displayName = "MarkdownH3";

export const MarkdownH4 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h4">) => (
    <h4
      className={cn(
        "text-sm font-semibold text-foreground/90 mt-2.5 mb-1",
        className
      )}
      {...props}
    >
      {children}
    </h4>
  )
);
MarkdownH4.displayName = "MarkdownH4";

export const MarkdownH5 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h5">) => (
    <h5
      className={cn(
        "text-xs font-semibold uppercase tracking-wider text-muted-foreground mt-2 mb-1",
        className
      )}
      {...props}
    >
      {children}
    </h5>
  )
);
MarkdownH5.displayName = "MarkdownH5";

export const MarkdownH6 = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"h6">) => (
    <h6
      className={cn(
        "text-xs font-semibold uppercase tracking-wider text-muted-foreground/80 mt-2 mb-1",
        className
      )}
      {...props}
    >
      {children}
    </h6>
  )
);
MarkdownH6.displayName = "MarkdownH6";
