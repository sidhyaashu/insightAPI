"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { ExternalLinkIcon } from "lucide-react";
import type { ComponentProps } from "react";

export type InlineCitationProps = ComponentProps<"span">;

export const InlineCitation = ({ className, ...props }: InlineCitationProps) => (
  <span className={cn("group inline items-center gap-1 font-mono text-xs", className)} {...props} />
);

export type InlineCitationTriggerProps = ComponentProps<typeof Badge> & {
  sourceUrl: string;
  label?: string;
};

export const InlineCitationTrigger = ({
  sourceUrl,
  label,
  className,
  ...props
}: InlineCitationTriggerProps) => {
  let hostname = "endpoint";
  try {
    hostname = new URL(sourceUrl).hostname;
  } catch {}

  return (
    <a href={sourceUrl} target="_blank" rel="noreferrer" className="inline-block no-underline">
      <Badge
        className={cn(
          "ml-1 cursor-pointer gap-1 px-1.5 py-0.5 font-mono text-[10px] font-normal hover:bg-primary/20 transition-colors",
          className
        )}
        variant="secondary"
        {...props}
      >
        <span>{label || hostname}</span>
        <ExternalLinkIcon className="size-2.5 opacity-70" />
      </Badge>
    </a>
  );
};
