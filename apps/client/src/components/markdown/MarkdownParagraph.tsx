"use client";

import React, { memo } from "react";
import { cn } from "@/lib/utils";

export const MarkdownParagraph = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"p">) => {
    return (
      <p
        className={cn(
          "my-2 text-xs sm:text-sm text-foreground/95 leading-relaxed break-words font-normal",
          className
        )}
        {...props}
      >
        {children}
      </p>
    );
  }
);

MarkdownParagraph.displayName = "MarkdownParagraph";
