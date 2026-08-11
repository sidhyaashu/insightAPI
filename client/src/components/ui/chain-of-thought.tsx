"use client";

import React, { createContext, memo, useContext, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import { WorkflowIcon, ChevronDownIcon, CheckCircle2Icon, Loader2Icon, CircleIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

interface ChainOfThoughtContextValue {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

const ChainOfThoughtContext = createContext<ChainOfThoughtContextValue | null>(null);

const useChainOfThought = () => {
  const context = useContext(ChainOfThoughtContext);
  if (!context) {
    throw new Error("ChainOfThought components must be used within ChainOfThought");
  }
  return context;
};

export type ChainOfThoughtProps = ComponentProps<"div"> & {
  open?: boolean;
  defaultOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export const ChainOfThought = memo(
  ({
    className,
    open,
    defaultOpen = false,
    onOpenChange,
    children,
    ...props
  }: ChainOfThoughtProps) => {
    const [isOpenState, setIsOpenState] = useState(defaultOpen);
    const isControlled = open !== undefined;
    const isOpen = isControlled ? open : isOpenState;

    const setIsOpen = (next: boolean) => {
      if (!isControlled) setIsOpenState(next);
      onOpenChange?.(next);
    };

    const chainOfThoughtContext = useMemo(
      () => ({ isOpen, setIsOpen }),
      [isOpen, setIsOpen]
    );

    return (
      <ChainOfThoughtContext.Provider value={chainOfThoughtContext}>
        <div className={cn("not-prose w-full space-y-3 my-2", className)} {...props}>
          {children}
        </div>
      </ChainOfThoughtContext.Provider>
    );
  }
);

export type ChainOfThoughtHeaderProps = ComponentProps<typeof CollapsibleTrigger>;

export const ChainOfThoughtHeader = memo(
  ({ className, children, ...props }: ChainOfThoughtHeaderProps) => {
    const { isOpen, setIsOpen } = useChainOfThought();

    return (
      <Collapsible onOpenChange={setIsOpen} open={isOpen}>
        <CollapsibleTrigger
          className={cn(
            "flex w-full items-center gap-2.5 rounded-lg border border-border/60 bg-muted/30 px-3.5 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground cursor-pointer shadow-xs",
            className
          )}
          {...props}
        >
          <WorkflowIcon className="size-3.5 text-muted-foreground shrink-0" />
          <span className="flex-1 text-left font-mono font-medium">
            {children ?? "Reasoning & Process Steps"}
          </span>
          <ChevronDownIcon
            className={cn(
              "size-3.5 shrink-0 text-muted-foreground transition-transform duration-200",
              isOpen ? "rotate-180" : "rotate-0"
            )}
          />
        </CollapsibleTrigger>
      </Collapsible>
    );
  }
);

export type ChainOfThoughtStepProps = ComponentProps<"div"> & {
  icon?: LucideIcon;
  label: ReactNode;
  description?: ReactNode;
  status?: "complete" | "active" | "pending";
};

const stepStatusStyles = {
  active: "text-foreground font-semibold",
  complete: "text-muted-foreground",
  pending: "text-muted-foreground/40",
};

export const ChainOfThoughtStep = memo(
  ({
    className,
    label,
    description,
    status = "complete",
    children,
    ...props
  }: ChainOfThoughtStepProps) => (
    <div
      className={cn(
        "flex gap-2.5 text-xs transition-all",
        stepStatusStyles[status],
        className
      )}
      {...props}
    >
      <div className="relative mt-0.5 flex flex-col items-center">
        {status === "complete" && <CheckCircle2Icon className="size-3.5 text-emerald-500 shrink-0" />}
        {status === "active" && <Loader2Icon className="size-3.5 text-foreground animate-spin shrink-0" />}
        {status === "pending" && <CircleIcon className="size-3.5 text-muted-foreground/40 shrink-0" />}
        <div className="mt-1 flex-1 w-px bg-border/40 min-h-[12px]" />
      </div>
      <div className="flex-1 space-y-1 overflow-hidden pb-2">
        <div className="font-mono text-xs">{label}</div>
        {description && (
          <div className="text-muted-foreground text-[11px] font-sans leading-relaxed">{description}</div>
        )}
        {children}
      </div>
    </div>
  )
);

export type ChainOfThoughtSearchResultsProps = ComponentProps<"div">;

export const ChainOfThoughtSearchResults = memo(
  ({ className, ...props }: ChainOfThoughtSearchResultsProps) => (
    <div
      className={cn("flex flex-wrap items-center gap-1.5 pt-1", className)}
      {...props}
    />
  )
);

export type ChainOfThoughtSearchResultProps = ComponentProps<typeof Badge>;

export const ChainOfThoughtSearchResult = memo(
  ({ className, children, ...props }: ChainOfThoughtSearchResultProps) => (
    <Badge
      className={cn("gap-1 px-2 py-0.5 font-mono text-[10px] bg-muted/50 hover:bg-muted text-foreground border-border/40 font-normal", className)}
      variant="secondary"
      {...props}
    >
      {children}
    </Badge>
  )
);

export type ChainOfThoughtContentProps = ComponentProps<typeof CollapsibleContent>;

export const ChainOfThoughtContent = memo(
  ({ className, children, ...props }: ChainOfThoughtContentProps) => {
    const { isOpen } = useChainOfThought();

    return (
      <Collapsible open={isOpen}>
        <CollapsibleContent
          className={cn(
            "mt-2 space-y-3 rounded-lg border border-border/60 bg-card/60 p-3 text-popover-foreground outline-none shadow-xs",
            className
          )}
          {...props}
        >
          {children}
        </CollapsibleContent>
      </Collapsible>
    );
  }
);

ChainOfThought.displayName = "ChainOfThought";
ChainOfThoughtHeader.displayName = "ChainOfThoughtHeader";
ChainOfThoughtStep.displayName = "ChainOfThoughtStep";
ChainOfThoughtSearchResults.displayName = "ChainOfThoughtSearchResults";
ChainOfThoughtSearchResult.displayName = "ChainOfThoughtSearchResult";
ChainOfThoughtContent.displayName = "ChainOfThoughtContent";
