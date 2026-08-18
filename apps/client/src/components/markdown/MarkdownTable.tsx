"use client";

import React, { memo } from "react";
import { cn } from "@/lib/utils";

export const MarkdownTable = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"table">) => {
    return (
      <div className="my-4 w-full overflow-hidden rounded-xl border border-border/70 bg-card/40 shadow-xs">
        <div className="overflow-x-auto">
          <table
            className={cn(
              "w-full text-left text-xs sm:text-sm border-collapse",
              className
            )}
            {...props}
          >
            {children}
          </table>
        </div>
      </div>
    );
  }
);

MarkdownTable.displayName = "MarkdownTable";

export const MarkdownTableHead = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"thead">) => {
    return (
      <thead
        className={cn(
          "bg-muted/60 dark:bg-muted/30 border-b border-border/70 text-foreground font-semibold",
          className
        )}
        {...props}
      >
        {children}
      </thead>
    );
  }
);

MarkdownTableHead.displayName = "MarkdownTableHead";

export const MarkdownTableBody = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"tbody">) => {
    return (
      <tbody
        className={cn("divide-y divide-border/40 text-foreground", className)}
        {...props}
      >
        {children}
      </tbody>
    );
  }
);

MarkdownTableBody.displayName = "MarkdownTableBody";

export const MarkdownTableRow = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"tr">) => {
    return (
      <tr
        className={cn(
          "hover:bg-muted/30 transition-colors even:bg-muted/10",
          className
        )}
        {...props}
      >
        {children}
      </tr>
    );
  }
);

MarkdownTableRow.displayName = "MarkdownTableRow";

export const MarkdownTableHeaderCell = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"th">) => {
    return (
      <th
        className={cn(
          "p-3 font-semibold tracking-wide text-xs text-foreground/90 whitespace-nowrap",
          className
        )}
        {...props}
      >
        {children}
      </th>
    );
  }
);

MarkdownTableHeaderCell.displayName = "MarkdownTableHeaderCell";

export const MarkdownTableCell = memo(
  ({ children, className, ...props }: React.ComponentPropsWithoutRef<"td">) => {
    return (
      <td
        className={cn("p-3 align-top leading-relaxed break-words", className)}
        {...props}
      >
        {children}
      </td>
    );
  }
);

MarkdownTableCell.displayName = "MarkdownTableCell";
