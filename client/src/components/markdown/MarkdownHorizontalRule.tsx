"use client";

import React, { memo } from "react";
import { cn } from "@/lib/utils";

export const MarkdownHorizontalRule = memo(
  ({ className, ...props }: React.ComponentPropsWithoutRef<"hr">) => {
    return (
      <hr
        className={cn("my-4 border-0 border-t border-border/60", className)}
        {...props}
      />
    );
  }
);

MarkdownHorizontalRule.displayName = "MarkdownHorizontalRule";
